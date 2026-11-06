"""DNS管理系统 - Flask Web应用"""
import hashlib
import json
import os
import platform
import sys
import time
import threading
from datetime import datetime, timedelta
from functools import wraps

import pymysql
import psutil
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify

import config
from dns_server import DNSServer

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.permanent_session_lifetime = timedelta(minutes=config.COOKIE_MAX_AGE)

# 全局DNS服务器实例
dns_server = None


def get_db():
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


def get_sysconfig(key, default=''):
    """获取系统配置"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT cval FROM wd_sysconfig WHERE ckey=%s", (key,))
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else default
    except:
        return default
    finally:
        if conn:
            try: conn.close()
            except: pass


def set_sysconfig(key, value):
    """设置系统配置"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM wd_sysconfig WHERE ckey=%s", (key,))
        if cursor.fetchone():
            cursor.execute("UPDATE wd_sysconfig SET cval=%s WHERE ckey=%s", (value, key))
        else:
            cursor.execute("INSERT INTO wd_sysconfig (ckey, cval, rtime) VALUES (%s, %s, NOW())", (key, value))
        cursor.close()
    except:
        pass
    finally:
        if conn:
            try: conn.close()
            except: pass


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def make_password(password, salt):
    """生成密码哈希"""
    return hashlib.sha256((password + salt).encode()).hexdigest()


def get_admin_name():
    """获取后台名称"""
    return get_sysconfig('admin_name', config.ADMIN_NAME)


# ==================== 页面路由 ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM wd_member WHERE username=%s", (username,))
            user = cursor.fetchone()
            cursor.close()

            if user and user['password'] == make_password(password, user['salt']):
                session.permanent = True
                session['username'] = username
                session['uid'] = user['id']
                # 更新登录时间
                conn2 = get_db()
                c2 = conn2.cursor()
                c2.execute("UPDATE wd_member SET rtime=NOW() WHERE id=%s", (user['id'],))
                c2.close()
                conn2.close()
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='用户名或密码错误')
        except Exception as e:
            return render_template('login.html', error=f'登录失败: {str(e)}')
        finally:
            if conn:
                try: conn.close()
                except: pass
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 获取上次登录信息
        cursor.execute("SELECT rtime FROM wd_member WHERE id=%s", (session['uid'],))
        user = cursor.fetchone()
        last_login = str(user['rtime']) if user and user['rtime'] else '首次登录'

        # 获取系统资源使用率
        cpu_usage = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        mem_usage = mem.percent
        disk = psutil.disk_usage('/')
        disk_usage = round(disk.percent)

        # 今日查询数
        today_start = int(time.time()) - (int(time.time()) % 86400)
        cursor.execute("SELECT COALESCE(SUM(qc),0) as total FROM wd_querylog WHERE tn>=%s", (today_start,))
        today_queries = cursor.fetchone()['total']

        # 统计
        cursor.execute("SELECT COUNT(*) as c FROM wd_domain")
        domain_count = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM wd_record WHERE state=0")
        record_count = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM wd_server")
        server_count = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM wd_ptr WHERE state=0")
        ptr_count = cursor.fetchone()['c']

        # 24小时图表数据
        chart_labels = []
        chart_data = []
        now = datetime.now()
        for i in range(23, -1, -1):
            h = now - timedelta(hours=i)
            chart_labels.append(h.strftime('%H:00'))
            start_ts = int(h.replace(minute=0, second=0).timestamp())
            end_ts = start_ts + 3600
            cursor.execute("SELECT COALESCE(SUM(qc),0) as c FROM wd_querylog WHERE tn>=%s AND tn<%s", (start_ts, end_ts))
            chart_data.append(cursor.fetchone()['c'])

        cursor.close()
        return render_template('index.html',
            active_page='index',
            last_login=last_login,
            last_ip=request.remote_addr,
            cpu_usage=cpu_usage,
            mem_usage=mem_usage,
            disk_usage=disk_usage,
            today_queries=today_queries,
            domain_count=domain_count,
            record_count=record_count,
            server_count=server_count,
            ptr_count=ptr_count,
            chart_labels=chart_labels,
            chart_data=chart_data,
            admin_name=get_admin_name()
        )
    except Exception as e:
        flash(f'加载首页失败: {str(e)}', 'danger')
        return render_template('index.html', active_page='index', admin_name=get_admin_name(),
            last_login='-', last_ip='-', cpu_usage=0, mem_usage=0, disk_usage=0,
            today_queries=0, domain_count=0, record_count=0, server_count=0, ptr_count=0,
            chart_labels=[], chart_data=[])
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/domain')
@login_required
def domain_page():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        page = int(request.args.get('page', 1))
        keyword = request.args.get('keyword', '').strip()
        per_page = 20

        where = "WHERE 1=1"
        params = []
        if keyword:
            where += " AND domain LIKE %s"
            params.append(f'%{keyword}%')

        cursor.execute(f"SELECT COUNT(*) as c FROM wd_domain {where}", params)
        total = cursor.fetchone()['c']
        total_pages = max(1, (total + per_page - 1) // per_page)

        cursor.execute(f"SELECT * FROM wd_domain {where} ORDER BY id DESC LIMIT %s OFFSET %s",
                       params + [per_page, (page - 1) * per_page])
        domains = cursor.fetchall()
        cursor.close()

        return render_template('domain.html', active_page='domain', admin_name=get_admin_name(),
            domains=domains, page=page, total_pages=total_pages, keyword=keyword)
    except Exception as e:
        flash(str(e), 'danger')
        return render_template('domain.html', active_page='domain', admin_name=get_admin_name(),
            domains=[], page=1, total_pages=1, keyword='')
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/record')
@login_required
def record_page():
    conn = None
    try:
        did = int(request.args.get('did', 0))
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM wd_domain WHERE id=%s", (did,))
        domain_info = cursor.fetchone()
        if not domain_info:
            flash('域名不存在', 'danger')
            return redirect(url_for('domain_page'))

        cursor.execute("SELECT * FROM wd_record WHERE did=%s ORDER BY id DESC", (did,))
        records = cursor.fetchall()
        cursor.close()

        return render_template('record.html', active_page='domain', admin_name=get_admin_name(),
            domain_info=domain_info, records=records)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('domain_page'))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/ptr')
@login_required
def ptr_page():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        page = int(request.args.get('page', 1))
        keyword = request.args.get('keyword', '').strip()
        per_page = 20

        where = "WHERE 1=1"
        params = []
        if keyword:
            where += " AND (ip LIKE %s OR domain LIKE %s)"
            params.extend([f'%{keyword}%', f'%{keyword}%'])

        cursor.execute(f"SELECT COUNT(*) as c FROM wd_ptr {where}", params)
        total = cursor.fetchone()['c']
        total_pages = max(1, (total + per_page - 1) // per_page)

        cursor.execute(f"SELECT * FROM wd_ptr {where} ORDER BY id DESC LIMIT %s OFFSET %s",
                       params + [per_page, (page - 1) * per_page])
        ptrs = cursor.fetchall()
        cursor.close()

        return render_template('ptr.html', active_page='ptr', admin_name=get_admin_name(),
            ptrs=ptrs, page=page, total_pages=total_pages, keyword=keyword)
    except:
        return render_template('ptr.html', active_page='ptr', admin_name=get_admin_name(),
            ptrs=[], page=1, total_pages=1, keyword='')
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/forward')
@login_required
def forward_page():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM wd_nsg LIMIT 1")
        forward_setting = cursor.fetchone()
        if not forward_setting:
            forward_setting = {'id': 0, 'name': 'default', 'ns': ','.join(config.UPSTREAM_DNS), 'ttl': config.DNS_CACHE_TTL, 'state': 0}

        cursor.execute("SELECT * FROM wd_nsg ORDER BY id DESC")
        groups = cursor.fetchall()
        cursor.close()

        return render_template('forward.html', active_page='forward', admin_name=get_admin_name(),
            forward_setting=forward_setting, groups=groups)
    except:
        return render_template('forward.html', active_page='forward', admin_name=get_admin_name(),
            forward_setting={'ns': '', 'ttl': 60, 'state': 0}, groups=[])
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/cfw')
@login_required
def cfw_page():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM wd_cfw ORDER BY id DESC")
        cfws = cursor.fetchall()
        cfw_enabled = get_sysconfig('enable_cfw', '0') == '1'
        cursor.close()

        return render_template('cfw.html', active_page='cfw', admin_name=get_admin_name(),
            cfws=cfws, cfw_enabled=cfw_enabled)
    except:
        return render_template('cfw.html', active_page='cfw', admin_name=get_admin_name(),
            cfws=[], cfw_enabled=False)
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/server')
@login_required
def server_page():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM wd_server ORDER BY id DESC")
        servers = cursor.fetchall()
        cursor.close()

        return render_template('server.html', active_page='server', admin_name=get_admin_name(),
            servers=servers)
    except:
        return render_template('server.html', active_page='server', admin_name=get_admin_name(),
            servers=[])
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/query')
@login_required
def query_page():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        time_range = request.args.get('range', 'today')
        now = datetime.now()

        if time_range == 'realtime':
            start_ts = int(now.replace(minute=0, second=0).timestamp()) - 3600
            end_ts = int(now.timestamp())
            interval = 300  # 5分钟
            fmt = '%H:%M'
        elif time_range == '3h':
            start_ts = int(now.timestamp()) - 10800
            end_ts = int(now.timestamp())
            interval = 900
            fmt = '%H:%M'
        elif time_range == 'yesterday':
            yesterday = now - timedelta(days=1)
            start_ts = int(yesterday.replace(hour=0, minute=0, second=0).timestamp())
            end_ts = start_ts + 86400
            interval = 3600
            fmt = '%H:00'
        elif time_range == 'week':
            start_ts = int((now - timedelta(days=7)).replace(hour=0, minute=0, second=0).timestamp())
            end_ts = int(now.timestamp())
            interval = 86400
            fmt = '%m-%d'
        elif time_range == 'month':
            start_ts = int(now.replace(day=1, hour=0, minute=0, second=0).timestamp())
            end_ts = int(now.timestamp())
            interval = 86400
            fmt = '%m-%d'
        else:  # today
            start_ts = int(now.replace(hour=0, minute=0, second=0).timestamp())
            end_ts = int(now.timestamp())
            interval = 3600
            fmt = '%H:00'

        chart_labels = []
        chart_data = []
        total_queries = 0
        peak_value = 0
        t = start_ts
        while t < end_ts:
            t_end = min(t + interval, end_ts)
            label = datetime.fromtimestamp(t).strftime(fmt)
            chart_labels.append(label)
            cursor.execute("SELECT COALESCE(SUM(qc),0) as c FROM wd_querylog WHERE tn>=%s AND tn<%s", (t, t_end))
            val = cursor.fetchone()['c']
            chart_data.append(val)
            total_queries += val
            peak_value = max(peak_value, val)
            t = t_end

        duration_min = max(1, (end_ts - start_ts) // 60)
        avg_per_min = round(total_queries / duration_min, 1)
        cursor.close()

        return render_template('query.html', active_page='query', admin_name=get_admin_name(),
            time_range=time_range, chart_labels=chart_labels, chart_data=chart_data,
            total_queries=total_queries, avg_per_min=avg_per_min, peak_value=peak_value)
    except Exception as e:
        print(f"[查询流量] 查询失败: {e}")
        return render_template('query.html', active_page='query', admin_name=get_admin_name(),
            time_range='today', chart_labels=[], chart_data=[],
            total_queries=0, avg_per_min=0, peak_value=0)
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/ranking')
@login_required
def ranking_page():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        time_range = request.args.get('range', 'today')
        now = datetime.now()

        if time_range == 'week':
            start_ts = int((now - timedelta(days=7)).replace(hour=0, minute=0, second=0).timestamp())
        elif time_range == 'month':
            start_ts = int(now.replace(day=1, hour=0, minute=0, second=0).timestamp())
        else:
            start_ts = int(now.replace(hour=0, minute=0, second=0).timestamp())

        cursor.execute(
            "SELECT domain, SUM(qc) as total FROM wd_querylog WHERE tn>=%s GROUP BY domain ORDER BY total DESC LIMIT 30",
            (start_ts,)
        )
        rows = cursor.fetchall()
        cursor.close()

        max_total = rows[0]['total'] if rows else 1
        rankings = []
        for r in rows:
            rankings.append({
                'domain': r['domain'],
                'qc': r['total'],
                'percent': round(r['total'] / max_total * 100, 1) if max_total > 0 else 0
            })

        return render_template('ranking.html', active_page='ranking', admin_name=get_admin_name(),
            time_range=time_range, rankings=rankings)
    except Exception as e:
        print(f"[排行统计] 查询失败: {e}")
        return render_template('ranking.html', active_page='ranking', admin_name=get_admin_name(),
            time_range='today', rankings=[])
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/latest')
@login_required
def latest_page():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT domain, qtype, client_ip, forward, qc, rtime FROM wd_querylog ORDER BY id DESC LIMIT 100"
        )
        logs = cursor.fetchall()
        cursor.close()

        # forward字段转换为布尔值
        for log in logs:
            log['forward'] = bool(log.get('forward', 0))
            if not log.get('qtype'):
                log['qtype'] = 'A'
            if not log.get('client_ip'):
                log['client_ip'] = '-'

        return render_template('latest.html', active_page='latest', admin_name=get_admin_name(), logs=logs)
    except Exception as e:
        print(f"[最新记录] 查询失败: {e}")
        return render_template('latest.html', active_page='latest', admin_name=get_admin_name(), logs=[])
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/admin-settings')
@login_required
def admin_settings_page():
    settings = {
        'admin_name': get_sysconfig('admin_name', config.ADMIN_NAME),
        'admin_port': get_sysconfig('admin_port', str(config.WEB_PORT)),
        'login_ips': get_sysconfig('login_ips', ''),
        'main_ip': get_sysconfig('main_ip', ''),
    }
    return render_template('admin_settings.html', active_page='admin_settings', admin_name=get_admin_name(),
        settings=settings)


@app.route('/system-settings')
@login_required
def system_settings_page():
    settings = {
        'cookie_time': get_sysconfig('cookie_time', str(config.COOKIE_MAX_AGE)),
        'dns_port': get_sysconfig('dns_port', str(config.DNS_PORT)),
        'dns_cache_ttl': get_sysconfig('dns_cache_ttl', str(config.DNS_CACHE_TTL)),
    }
    sys_info = {
        'os': f'{platform.system()} {platform.release()}',
        'python': platform.python_version(),
        'web_port': config.WEB_PORT,
        'dns_port': config.DNS_PORT,
    }
    return render_template('system_settings.html', active_page='system_settings', admin_name=get_admin_name(),
        settings=settings, sys_info=sys_info)


@app.route('/change-password')
@login_required
def change_password_page():
    return render_template('change_password.html', active_page='change_password', admin_name=get_admin_name())


# ==================== API路由 ====================

@app.route('/api/domain/add', methods=['POST'])
@login_required
def api_domain_add():
    data = request.get_json()
    domain = data.get('domain', '').strip()
    note = data.get('note', '').strip()
    if not domain:
        return jsonify(code=1, msg='域名不能为空')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO wd_domain (domain, note, rtime, state) VALUES (%s, %s, NOW(), 0)", (domain, note))
        cursor.close()
        return jsonify(code=0, msg='添加成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/domain/edit', methods=['POST'])
@login_required
def api_domain_edit():
    data = request.get_json()
    did = data.get('id', 0)
    domain = data.get('domain', '').strip()
    note = data.get('note', '').strip()
    if not did or not domain:
        return jsonify(code=1, msg='参数错误')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE wd_domain SET domain=%s, note=%s WHERE id=%s", (domain, note, did))
        cursor.close()
        return jsonify(code=0, msg='修改成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/domain/delete', methods=['POST'])
@login_required
def api_domain_delete():
    data = request.get_json()
    did = data.get('id', 0)
    if not did:
        return jsonify(code=1, msg='参数错误')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM wd_record WHERE did=%s", (did,))
        cursor.execute("DELETE FROM wd_domain WHERE id=%s", (did,))
        cursor.close()
        return jsonify(code=0, msg='删除成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/record/add', methods=['POST'])
@login_required
def api_record_add():
    data = request.get_json()
    did = data.get('did', 0)
    domain = data.get('domain', '').strip()
    host = data.get('host', '').strip()
    qt = data.get('qt', 'A').strip()
    val = data.get('val', '').strip()
    ttl = int(data.get('ttl', 600))
    if not all([domain, host, val]):
        return jsonify(code=1, msg='参数不能为空')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO wd_record (did, domain, host, qt, val, ttl, rtime, state) VALUES (%s,%s,%s,%s,%s,%s,NOW(),0)",
            (did, domain, host, qt, val, ttl)
        )
        cursor.execute("UPDATE wd_domain SET `count`=(SELECT COUNT(*) FROM wd_record WHERE did=%s) WHERE id=%s", (did, did))
        cursor.close()
        return jsonify(code=0, msg='添加成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/record/edit', methods=['POST'])
@login_required
def api_record_edit():
    data = request.get_json()
    rid = data.get('id', 0)
    host = data.get('host', '').strip()
    qt = data.get('qt', 'A').strip()
    val = data.get('val', '').strip()
    ttl = int(data.get('ttl', 600))
    if not rid or not val:
        return jsonify(code=1, msg='参数错误')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE wd_record SET host=%s, qt=%s, val=%s, ttl=%s WHERE id=%s", (host, qt, val, ttl, rid))
        cursor.close()
        return jsonify(code=0, msg='修改成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/record/delete', methods=['POST'])
@login_required
def api_record_delete():
    data = request.get_json()
    rid = data.get('id', 0)
    if not rid:
        return jsonify(code=1, msg='参数错误')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT did FROM wd_record WHERE id=%s", (rid,))
        row = cursor.fetchone()
        did = row[0] if row else 0
        cursor.execute("DELETE FROM wd_record WHERE id=%s", (rid,))
        if did:
            cursor.execute("UPDATE wd_domain SET `count`=(SELECT COUNT(*) FROM wd_record WHERE did=%s) WHERE id=%s", (did, did))
        cursor.close()
        return jsonify(code=0, msg='删除成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/ptr/add', methods=['POST'])
@login_required
def api_ptr_add():
    data = request.get_json()
    ip = data.get('ip', '').strip()
    domain = data.get('domain', '').strip()
    ttl = int(data.get('ttl', 600))
    note = data.get('note', '').strip()
    if not ip or not domain:
        return jsonify(code=1, msg='IP和域名不能为空')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO wd_ptr (ip, domain, ttl, note, rtime, state) VALUES (%s,%s,%s,%s,NOW(),0)",
            (ip, domain, ttl, note)
        )
        cursor.close()
        return jsonify(code=0, msg='添加成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/ptr/edit', methods=['POST'])
@login_required
def api_ptr_edit():
    data = request.get_json()
    pid = data.get('id', 0)
    ip = data.get('ip', '').strip()
    domain = data.get('domain', '').strip()
    ttl = int(data.get('ttl', 600))
    note = data.get('note', '').strip()
    if not pid or not ip or not domain:
        return jsonify(code=1, msg='参数错误')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE wd_ptr SET ip=%s, domain=%s, ttl=%s, note=%s WHERE id=%s", (ip, domain, ttl, note, pid))
        cursor.close()
        return jsonify(code=0, msg='修改成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/ptr/delete', methods=['POST'])
@login_required
def api_ptr_delete():
    data = request.get_json()
    pid = data.get('id', 0)
    if not pid:
        return jsonify(code=1, msg='参数错误')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM wd_ptr WHERE id=%s", (pid,))
        cursor.close()
        return jsonify(code=0, msg='删除成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/forward/save', methods=['POST'])
@login_required
def api_forward_save():
    data = request.get_json()
    enable = data.get('enable_forward', True)
    ttl = int(data.get('ttl', 60))
    ns = data.get('upstream_dns', '').strip()
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM wd_nsg LIMIT 1")
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE wd_nsg SET ns=%s, ttl=%s, state=%s WHERE id=%s",
                         (ns, ttl, 0 if enable else 1, row[0]))
        else:
            cursor.execute("INSERT INTO wd_nsg (name, ns, ttl, rtime, state) VALUES ('default',%s,%s,NOW(),%s)",
                         (ns, ttl, 0 if enable else 1))
        # 更新全局配置
        config.ENABLE_FORWARD = enable
        config.UPSTREAM_DNS = ns.split(',') if ns else []
        config.DNS_CACHE_TTL = ttl
        cursor.close()
        return jsonify(code=0, msg='保存成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/forward/group/delete', methods=['POST'])
@login_required
def api_forward_group_delete():
    data = request.get_json()
    gid = data.get('id', 0)
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM wd_nsg WHERE id=%s", (gid,))
        cursor.close()
        return jsonify(code=0, msg='删除成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/cfw/add', methods=['POST'])
@login_required
def api_cfw_add():
    data = request.get_json()
    domain = data.get('domain', '').strip()
    ip = data.get('ip', '').strip()
    note = data.get('note', '').strip()
    if not domain or not ip:
        return jsonify(code=1, msg='域名和DNS服务器不能为空')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO wd_cfw (domain, ip, note, rtime, state) VALUES (%s,%s,%s,NOW(),0)",
                     (domain, ip, note))
        cursor.close()
        return jsonify(code=0, msg='添加成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/cfw/edit', methods=['POST'])
@login_required
def api_cfw_edit():
    data = request.get_json()
    cid = data.get('id', 0)
    domain = data.get('domain', '').strip()
    ip = data.get('ip', '').strip()
    note = data.get('note', '').strip()
    if not cid or not domain or not ip:
        return jsonify(code=1, msg='参数错误')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE wd_cfw SET domain=%s, ip=%s, note=%s WHERE id=%s", (domain, ip, note, cid))
        cursor.close()
        return jsonify(code=0, msg='修改成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/cfw/delete', methods=['POST'])
@login_required
def api_cfw_delete():
    data = request.get_json()
    cid = data.get('id', 0)
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM wd_cfw WHERE id=%s", (cid,))
        cursor.close()
        return jsonify(code=0, msg='删除成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/cfw/toggle', methods=['POST'])
@login_required
def api_cfw_toggle():
    data = request.get_json()
    enabled = data.get('enabled', False)
    set_sysconfig('enable_cfw', '1' if enabled else '0')
    config.ENABLE_CONDITIONAL_FORWARD = enabled
    return jsonify(code=0, msg='操作成功')


@app.route('/api/server/add', methods=['POST'])
@login_required
def api_server_add():
    data = request.get_json()
    ip = data.get('ip', '').strip()
    name = data.get('name', '').strip()
    if not ip or not name:
        return jsonify(code=1, msg='IP和名称不能为空')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO wd_server (ip, name, rtime, state) VALUES (%s,%s,NOW(),0)", (ip, name))
        cursor.close()
        return jsonify(code=0, msg='添加成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/server/edit', methods=['POST'])
@login_required
def api_server_edit():
    data = request.get_json()
    sid = data.get('id', 0)
    ip = data.get('ip', '').strip()
    name = data.get('name', '').strip()
    if not sid or not ip or not name:
        return jsonify(code=1, msg='参数错误')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE wd_server SET ip=%s, name=%s WHERE id=%s", (ip, name, sid))
        cursor.close()
        return jsonify(code=0, msg='修改成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/server/delete', methods=['POST'])
@login_required
def api_server_delete():
    data = request.get_json()
    sid = data.get('id', 0)
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM wd_server WHERE id=%s", (sid,))
        cursor.close()
        return jsonify(code=0, msg='删除成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


@app.route('/api/admin-settings/save', methods=['POST'])
@login_required
def api_admin_settings_save():
    data = request.get_json()
    set_sysconfig('admin_name', data.get('admin_name', ''))
    set_sysconfig('admin_port', data.get('admin_port', ''))
    set_sysconfig('login_ips', data.get('login_ips', ''))
    set_sysconfig('main_ip', data.get('main_ip', ''))
    return jsonify(code=0, msg='保存成功')


@app.route('/api/system-settings/save', methods=['POST'])
@login_required
def api_system_settings_save():
    data = request.get_json()
    set_sysconfig('cookie_time', str(data.get('cookie_time', '600')))
    set_sysconfig('dns_port', str(data.get('dns_port', '53')))
    set_sysconfig('dns_cache_ttl', str(data.get('dns_cache_ttl', '60')))
    return jsonify(code=0, msg='保存成功')


@app.route('/api/change-password', methods=['POST'])
@login_required
def api_change_password():
    data = request.get_json()
    old_pwd = data.get('old_password', '')
    new_pwd = data.get('new_password', '')
    if not old_pwd or not new_pwd:
        return jsonify(code=1, msg='请填写完整')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM wd_member WHERE id=%s", (session['uid'],))
        user = cursor.fetchone()
        if not user:
            return jsonify(code=1, msg='用户不存在')
        if user['password'] != make_password(old_pwd, user['salt']):
            return jsonify(code=1, msg='当前密码错误')
        new_hash = make_password(new_pwd, user['salt'])
        cursor2 = conn.cursor()
        cursor2.execute("UPDATE wd_member SET password=%s WHERE id=%s", (new_hash, session['uid']))
        cursor.close()
        cursor2.close()
        return jsonify(code=0, msg='密码修改成功')
    except Exception as e:
        return jsonify(code=1, msg=str(e))
    finally:
        if conn:
            try: conn.close()
            except: pass


# ==================== 启动入口 ====================

def start_dns_server():
    """在后台线程启动DNS服务器"""
    global dns_server
    dns_server = DNSServer()
    try:
        dns_server.start()
    except Exception as e:
        print(f"[DNS] 启动失败: {e}")


def init_db_if_needed():
    """如果数据库不存在则自动初始化，并迁移旧表结构"""
    conn = None
    try:
        conn = pymysql.connect(
            host=config.DB_CONFIG['host'],
            port=config.DB_CONFIG['port'],
            user=config.DB_CONFIG['user'],
            password=config.DB_CONFIG['password'],
            charset='utf8'
        )
        cursor = conn.cursor()
        cursor.execute(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='{config.DB_CONFIG['database']}'")
        if not cursor.fetchone():
            print("[初始化] 数据库不存在，正在创建...")
            cursor.close()
            conn.close()
            from init_db import init_database
            init_database()
            return

        # 迁移: 检查并添加 wd_querylog 缺失字段
        cursor.execute(f"USE `{config.DB_CONFIG['database']}`")
        migrations = [
            ("wd_querylog", "qtype", "ALTER TABLE `wd_querylog` ADD COLUMN `qtype` varchar(10) NOT NULL DEFAULT 'A' AFTER `domain`"),
            ("wd_querylog", "client_ip", "ALTER TABLE `wd_querylog` ADD COLUMN `client_ip` varchar(45) NOT NULL DEFAULT '' AFTER `qtype`"),
            ("wd_querylog", "forward", "ALTER TABLE `wd_querylog` ADD COLUMN `forward` tinyint(1) NOT NULL DEFAULT 0 AFTER `client_ip`"),
        ]
        for table, col, sql in migrations:
            try:
                cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='{config.DB_CONFIG['database']}' AND TABLE_NAME='{table}' AND COLUMN_NAME='{col}'")
                if not cursor.fetchone():
                    print(f"[迁移] 添加字段 {table}.{col}")
                    cursor.execute(sql)
            except Exception as e:
                print(f"[迁移] {table}.{col} 失败: {e}")

        # 添加索引
        for idx_sql in [
            "CREATE INDEX `idx_querylog_tn` ON `wd_querylog` (`tn`)",
            "CREATE INDEX `idx_querylog_domain` ON `wd_querylog` (`domain`)",
        ]:
            try:
                cursor.execute(idx_sql)
            except:
                pass

        cursor.close()
    except Exception as e:
        print(f"[初始化] 检查数据库失败: {e}")
    finally:
        if conn:
            try: conn.close()
            except: pass


if __name__ == '__main__':
    print("=" * 50)
    print("  DNS管理系统启动中...")
    print(f"  Web管理后台: http://127.0.0.1:{config.WEB_PORT}")
    print(f"  DNS服务端口: {config.DNS_PORT}")
    print(f"  默认账号: admin / admin")
    print("=" * 50)

    # 初始化数据库
    init_db_if_needed()

    # 启动DNS服务器（后台线程）
    dns_thread = threading.Thread(target=start_dns_server, daemon=True)
    dns_thread.start()

    # 启动Web服务
    app.run(host='0.0.0.0', port=config.WEB_PORT, debug=False)
