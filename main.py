"""DNS管理系统 - 主入口"""
import sys
import os

# 确保项目目录在Python路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """主入口函数"""
    print("=" * 50)
    print("  DNS管理系统")
    print("  正在启动...")
    print("=" * 50)

    # 导入并启动应用
    from app import app, start_dns_server, init_db_if_needed
    import config
    import threading

    # 初始化数据库
    init_db_if_needed()

    # 启动DNS服务器（后台线程）
    dns_thread = threading.Thread(target=start_dns_server, daemon=True)
    dns_thread.start()

    # 启动Web服务
    print(f"\n  Web管理后台: http://127.0.0.1:{config.WEB_PORT}")
    print(f"  DNS服务端口: {config.DNS_PORT}")
    print(f"  默认账号: admin / admin")
    print(f"\n  按 Ctrl+C 停止服务\n")

    app.run(host='0.0.0.0', port=config.WEB_PORT, debug=False)


if __name__ == '__main__':
    main()
