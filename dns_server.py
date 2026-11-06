"""DNS服务器核心 - 处理DNS查询请求"""
import socket
import struct
import threading
import time
import hashlib
import pymysql
import config


class DNSServer:
    """简易DNS服务器"""

    def __init__(self):
        self.cache = {}
        self.cache_lock = threading.Lock()
        self.running = True

    def get_db(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=config.DB_CONFIG['host'],
            port=config.DB_CONFIG['port'],
            user=config.DB_CONFIG['user'],
            password=config.DB_CONFIG['password'],
            database=config.DB_CONFIG['database'],
            charset=config.DB_CONFIG['charset'],
            autocommit=True
        )

    def parse_domain_name(self, data, offset):
        """从DNS数据包中解析域名"""
        domain_parts = []
        while offset < len(data):
            length = data[offset]
            if offset + 1 > len(data):
                break
            if length == 0:
                offset += 1
                break
            if (length & 0xC0) == 0xC0:
                if offset + 2 > len(data):
                    break
                pointer = struct.unpack('!H', data[offset:offset + 2])[0] & 0x3FFF
                sub_domain, _ = self.parse_domain_name(data, pointer)
                domain_parts.append(sub_domain)
                offset += 2
                return '.'.join(domain_parts), offset
            offset += 1
            if offset + length > len(data):
                break
            domain_parts.append(data[offset:offset + length].decode('utf-8', errors='ignore'))
            offset += length
        return '.'.join(domain_parts), offset

    def parse_dns_query(self, data):
        """解析DNS查询包"""
        if len(data) < 12:
            return None, None, None, None
        txn_id = struct.unpack('!H', data[0:2])[0]
        flags = struct.unpack('!H', data[2:4])[0]
        qdcount = struct.unpack('!H', data[4:6])[0]
        if qdcount < 1:
            return None, None, None, None
        offset = 12
        domain, offset = self.parse_domain_name(data, offset)
        if offset + 4 > len(data):
            return None, None, None, None
        qtype = struct.unpack('!H', data[offset:offset + 2])[0]
        qclass = struct.unpack('!H', data[offset + 2:offset + 4])[0]
        return txn_id, domain, qtype, qclass

    def build_dns_response(self, txn_id, domain, qtype, qclass, answer_data, flags=0x8180):
        """构建DNS响应包
        answer_data: 已经序列化好的二进制answer段
        flags: 响应标志, 0x8180=NOERROR, 0x8183=NXDOMAIN
        """
        # Header
        qdcount = 1
        ancount = answer_data.get('count', 0)
        header = struct.pack('!HHHHHH', txn_id, flags, qdcount, ancount, 0, 0)

        # Question section (原样复制)
        question = b''
        for part in domain.split('.'):
            question += struct.pack('B', len(part)) + part.encode()
        question += b'\x00' + struct.pack('!HH', qtype, qclass)

        # Answer section
        raw_answers = answer_data.get('raw', b'')

        return header + question + raw_answers

    def ip_to_rdata(self, ip):
        """将IP地址转换为A记录的rdata"""
        return socket.inet_aton(ip)

    def domain_to_rdata(self, domain):
        """将域名转换为DNS名称格式的rdata"""
        rdata = b''
        for part in domain.split('.'):
            rdata += struct.pack('B', len(part)) + part.encode()
        rdata += b'\x00'
        return rdata

    def build_answer_data(self, answers):
        """将答案列表构建为二进制answer段"""
        raw = b''
        for ans in answers:
            raw += b'\xc0\x0c'  # Pointer to domain name in question
            raw += struct.pack('!HH', ans['type'], 1)  # Type, Class IN
            raw += struct.pack('!I', ans.get('ttl', 60))  # TTL
            rdata = ans['rdata']
            raw += struct.pack('!H', len(rdata))  # RDLENGTH
            raw += rdata  # RDATA
        return {'count': len(answers), 'raw': raw}

    def forward_query(self, domain, qtype, qclass, original_txn_id):
        """转发查询到上游DNS服务器
        关键修复: 使用原始请求的txn_id, 而不是生成新的
        """
        # 为上游查询生成新的txn_id
        upstream_txn_id = int(hashlib.md5(str(time.time()).encode()).hexdigest()[:4], 16)
        query = struct.pack('!H', upstream_txn_id)
        query += struct.pack('!H', 0x0100)  # Standard query with RD=1
        query += struct.pack('!H', 1)  # QDCOUNT
        query += struct.pack('!HHH', 0, 0, 0)  # ANCOUNT, NSCOUNT, ARCOUNT

        # Question
        for part in domain.split('.'):
            query += struct.pack('B', len(part)) + part.encode()
        query += b'\x00' + struct.pack('!HH', qtype, qclass)

        for dns_server in config.UPSTREAM_DNS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(3)
                sock.sendto(query, (dns_server, 53))
                response, _ = sock.recvfrom(4096)
                sock.close()

                if len(response) < 12:
                    continue

                # 关键修复: 用原始请求的txn_id替换上游响应的txn_id
                # 这样客户端才能正确匹配请求和响应
                new_response = struct.pack('!H', original_txn_id) + response[2:]
                return new_response
            except Exception as e:
                print(f"[DNS] 转发到 {dns_server} 失败: {e}")
                continue
        return None

    def cache_result(self, domain, qtype, answer_data, ttl=60):
        """缓存DNS查询结果 (存储构建好的二进制数据)"""
        with self.cache_lock:
            cache_key = f"{domain}:{qtype}"
            self.cache[cache_key] = {
                'answer_data': answer_data,
                'time': time.time(),
                'ttl': ttl
            }

    def get_cached(self, domain, qtype):
        """获取缓存的DNS结果 (返回构建好的answer_data dict)"""
        with self.cache_lock:
            cache_key = f"{domain}:{qtype}"
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                if time.time() - entry['time'] < entry['ttl']:
                    return entry['answer_data']
                else:
                    del self.cache[cache_key]
        return None

    def split_domain(self, full_domain):
        """将完整域名拆分为 主机记录(host) + 主域名(domain)
        例如: www.example.com -> host='www', domain='example.com'
              example.com -> host='@', domain='example.com'
              a.b.example.com -> host='a.b', domain='example.com'
        """
        parts = full_domain.split('.')
        if len(parts) <= 2:
            return '@', full_domain
        # 尝试匹配: 最后两段作为主域名
        domain = '.'.join(parts[-2:])
        host = '.'.join(parts[:-2])
        return host, domain

    def lookup_records(self, full_domain, qtype):
        """从数据库查询DNS记录
        关键修复: 正确拆分子域名和主域名进行匹配
        """
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            type_map = {1: 'A', 2: 'NS', 5: 'CNAME', 6: 'SOA', 15: 'MX', 16: 'TXT', 28: 'AAAA'}
            qtype_str = type_map.get(qtype, str(qtype))

            # 拆分域名: www.example.com -> host='www', domain='example.com'
            host, domain = self.split_domain(full_domain)

            records = []

            # 第1步: 精确匹配 host + domain
            cursor.execute(
                "SELECT val, ttl FROM wd_record WHERE domain=%s AND host=%s AND qt=%s AND state=0",
                (domain, host, qtype_str)
            )
            records = cursor.fetchall()

            # 第2步: 尝试通配符匹配 host='*'
            if not records:
                cursor.execute(
                    "SELECT val, ttl FROM wd_record WHERE domain=%s AND host='*' AND qt=%s AND state=0",
                    (domain, qtype_str)
                )
                records = cursor.fetchall()

            # 第3步: 尝试完整域名作为domain, host='@'
            if not records:
                cursor.execute(
                    "SELECT val, ttl FROM wd_record WHERE domain=%s AND host='@' AND qt=%s AND state=0",
                    (full_domain, qtype_str)
                )
                records = cursor.fetchall()

            # 第4步: 尝试三级域名场景 (如 a.b.example.com)
            if not records and len(full_domain.split('.')) > 3:
                parts = full_domain.split('.')
                # 尝试 host='a.b', domain='example.com' 已在第1步
                # 再尝试 host='b', domain='example.com'
                sub_host = parts[-3]
                sub_domain = '.'.join(parts[-2:])
                cursor.execute(
                    "SELECT val, ttl FROM wd_record WHERE domain=%s AND host=%s AND qt=%s AND state=0",
                    (sub_domain, sub_host, qtype_str)
                )
                records = cursor.fetchall()

            cursor.close()
            return records
        except Exception as e:
            print(f"[DNS] 查询数据库失败: {e}")
            return []
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def lookup_cfw(self, domain):
        """查询条件转发规则"""
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            # 精确匹配域名
            cursor.execute(
                "SELECT ip FROM wd_cfw WHERE domain=%s AND state=0",
                (domain,)
            )
            record = cursor.fetchone()
            # 匹配父域名
            if not record:
                _, parent_domain = self.split_domain(domain)
                cursor.execute(
                    "SELECT ip FROM wd_cfw WHERE domain=%s AND state=0",
                    (parent_domain,)
                )
                record = cursor.fetchone()
            cursor.close()
            return record
        except Exception as e:
            print(f"[DNS] 查询条件转发失败: {e}")
            return None
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def forward_to_specific_dns(self, domain, qtype, qclass, original_txn_id, target_dns):
        """转发查询到指定的DNS服务器 (条件转发)"""
        upstream_txn_id = int(hashlib.md5(str(time.time()).encode()).hexdigest()[:4], 16)
        query = struct.pack('!H', upstream_txn_id)
        query += struct.pack('!H', 0x0100)
        query += struct.pack('!H', 1)
        query += struct.pack('!HHH', 0, 0, 0)

        for part in domain.split('.'):
            query += struct.pack('B', len(part)) + part.encode()
        query += b'\x00' + struct.pack('!HH', qtype, qclass)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            sock.sendto(query, (target_dns, 53))
            response, _ = sock.recvfrom(4096)
            sock.close()

            if len(response) < 12:
                return None

            new_response = struct.pack('!H', original_txn_id) + response[2:]
            return new_response
        except Exception as e:
            print(f"[DNS] 条件转发到 {target_dns} 失败: {e}")
            return None

    def lookup_ptr(self, ip_query):
        """从数据库查询PTR记录"""
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT domain, ttl FROM wd_ptr WHERE ip=%s AND state=0", (ip_query,))
            records = cursor.fetchall()
            cursor.close()
            return records
        except Exception as e:
            print(f"[DNS] 查询PTR记录失败: {e}")
            return []
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def log_query(self, domain, client_ip, qtype, forward=False):
        """记录DNS查询日志
        逻辑: 同一域名+同一来源IP+同一类型，当天只累加qc；否则新增行
        """
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            now_ts = int(time.time())
            today_start = now_ts - (now_ts % 86400)
            qtype_str = {1: 'A', 2: 'NS', 5: 'CNAME', 6: 'SOA', 12: 'PTR', 15: 'MX', 16: 'TXT', 28: 'AAAA'}.get(qtype, str(qtype))
            fwd = 1 if forward else 0

            # 尝试更新今天同域名+同client_ip+同qtype的记录的qc
            cursor.execute(
                "UPDATE wd_querylog SET qc=qc+1 WHERE domain=%s AND client_ip=%s AND qtype=%s AND tn>=%s",
                (domain, client_ip, qtype_str, today_start)
            )
            if cursor.rowcount == 0:
                # 没有匹配记录，插入新行
                cursor.execute(
                    "INSERT INTO wd_querylog (domain, qtype, client_ip, forward, qc, tn, rtime) VALUES (%s,%s,%s,%s,1,%s,NOW())",
                    (domain, qtype_str, client_ip, fwd, now_ts)
                )
            cursor.close()
        except Exception as e:
            print(f"[DNS] 记录查询日志失败: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def handle_query(self, data, addr, sock):
        """处理DNS查询"""
        try:
            txn_id, domain, qtype, qclass = self.parse_dns_query(data)
            if domain is None:
                return

            client_ip = addr[0]
            print(f"[DNS] 查询: {domain} type={qtype} from {client_ip}")

            # ========== 1. 检查缓存 ==========
            cached = self.get_cached(domain, qtype)
            if cached:
                response = self.build_dns_response(txn_id, domain, qtype, qclass, cached)
                sock.sendto(response, addr)
                threading.Thread(target=self.log_query, args=(domain, client_ip, qtype, False), daemon=True).start()
                return

            # ========== 2. PTR查询 (反向解析) ==========
            if qtype == 12:
                ip_parts = domain.replace('.in-addr.arpa', '').split('.')
                ip_query = '.'.join(reversed(ip_parts))
                records = self.lookup_ptr(ip_query)
                if records:
                    answers = []
                    for rec in records:
                        answers.append({
                            'type': 12,  # PTR
                            'ttl': rec[1] if rec[1] > 0 else 60,
                            'rdata': self.domain_to_rdata(rec[0])
                        })
                    answer_data = self.build_answer_data(answers)
                    response = self.build_dns_response(txn_id, domain, qtype, qclass, answer_data)
                    self.cache_result(domain, qtype, answer_data)
                    sock.sendto(response, addr)
                    threading.Thread(target=self.log_query, args=(domain, client_ip, qtype, False), daemon=True).start()
                    return

            # ========== 3. 条件转发检查 ==========
            if config.ENABLE_CONDITIONAL_FORWARD:
                cfw = self.lookup_cfw(domain)
                if cfw and cfw.get('ip'):
                    target_dns = cfw['ip'].strip()
                    print(f"[DNS] 条件转发: {domain} -> {target_dns}")
                    forwarded = self.forward_to_specific_dns(domain, qtype, qclass, txn_id, target_dns)
                    if forwarded:
                        sock.sendto(forwarded, addr)
                        threading.Thread(target=self.log_query, args=(domain, client_ip, qtype, True), daemon=True).start()
                        return

            # ========== 4. 查询本地数据库记录 ==========
            records = self.lookup_records(domain, qtype)
            if records and len(records) > 0:
                answers = []
                for rec in records:
                    val = rec['val'] if isinstance(rec, dict) else rec[0]
                    ttl = (rec['ttl'] if isinstance(rec, dict) else rec[1]) or 60
                    if ttl <= 0:
                        ttl = 60

                    if qtype == 1:  # A record
                        try:
                            answers.append({'type': 1, 'ttl': ttl, 'rdata': self.ip_to_rdata(val)})
                        except Exception:
                            pass
                    elif qtype == 28:  # AAAA record
                        try:
                            answers.append({'type': 28, 'ttl': ttl, 'rdata': socket.inet_pton(socket.AF_INET6, val)})
                        except Exception:
                            pass
                    elif qtype == 5:  # CNAME
                        answers.append({'type': 5, 'ttl': ttl, 'rdata': self.domain_to_rdata(val)})
                    elif qtype == 15:  # MX
                        rdata = struct.pack('!H', 10) + self.domain_to_rdata(val)
                        answers.append({'type': 15, 'ttl': ttl, 'rdata': rdata})
                    elif qtype == 2:  # NS
                        answers.append({'type': 2, 'ttl': ttl, 'rdata': self.domain_to_rdata(val)})
                    elif qtype == 16:  # TXT
                        txt_data = val.encode('utf-8')[:255]
                        rdata = struct.pack('B', len(txt_data)) + txt_data
                        answers.append({'type': 16, 'ttl': ttl, 'rdata': rdata})

                if answers:
                    answer_data = self.build_answer_data(answers)
                    response = self.build_dns_response(txn_id, domain, qtype, qclass, answer_data)
                    self.cache_result(domain, qtype, answer_data, answers[0]['ttl'])
                    sock.sendto(response, addr)
                    threading.Thread(target=self.log_query, args=(domain, client_ip, qtype, False), daemon=True).start()
                    return

            # ========== 5. 转发到上级DNS (递归查询) ==========
            if config.ENABLE_FORWARD:
                forwarded = self.forward_query(domain, qtype, qclass, txn_id)
                if forwarded:
                    sock.sendto(forwarded, addr)
                    threading.Thread(target=self.log_query, args=(domain, client_ip, qtype, True), daemon=True).start()
                    return

            # ========== 6. 返回 NXDOMAIN (域名不存在) ==========
            empty_answer = {'count': 0, 'raw': b''}
            response = self.build_dns_response(txn_id, domain, qtype, qclass, empty_answer, flags=0x8183)
            sock.sendto(response, addr)
            threading.Thread(target=self.log_query, args=(domain, client_ip, qtype, False), daemon=True).start()

        except Exception as e:
            print(f"[DNS] 处理查询错误: {e}")

    def start(self):
        """启动DNS服务器"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', config.DNS_PORT))
        print(f"[DNS] 服务器启动在端口 {config.DNS_PORT} (UDP)")
        print(f"[DNS] 递归转发: {'开启' if config.ENABLE_FORWARD else '关闭'}")
        print(f"[DNS] 条件转发: {'开启' if config.ENABLE_CONDITIONAL_FORWARD else '关闭'}")
        print(f"[DNS] 上游DNS: {config.UPSTREAM_DNS}")

        while self.running:
            try:
                sock.settimeout(1)
                try:
                    data, addr = sock.recvfrom(4096)
                except socket.timeout:
                    continue
                threading.Thread(target=self.handle_query, args=(data, addr, sock), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"[DNS] 错误: {e}")
        sock.close()

    def stop(self):
        """停止DNS服务器"""
        self.running = False
