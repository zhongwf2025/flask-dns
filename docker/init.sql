-- DNS管理系统 数据库初始化脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS `dns` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `dns`;

-- 用户表
CREATE TABLE IF NOT EXISTS `wd_member` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `gid` int(11) NOT NULL DEFAULT 10,
    `nid` int(11) NOT NULL DEFAULT 0,
    `username` varchar(20) NOT NULL DEFAULT '',
    `password` varchar(64) NOT NULL DEFAULT '',
    `salt` varchar(255) NOT NULL DEFAULT '',
    `email` varchar(50) NOT NULL DEFAULT '',
    `phone` varchar(20) NOT NULL DEFAULT '',
    `wx` varchar(30) NOT NULL DEFAULT '',
    `xm` varchar(255) NOT NULL DEFAULT '',
    `sfz` varchar(255) NOT NULL DEFAULT '',
    `pic1` varchar(255) NOT NULL DEFAULT '',
    `pic2` varchar(255) NOT NULL DEFAULT '',
    `eis` int(11) NOT NULL DEFAULT 0,
    `pis` int(11) NOT NULL DEFAULT 0,
    `isx` int(11) NOT NULL DEFAULT 0,
    `cny` double NOT NULL DEFAULT 0,
    `note` varchar(100) NOT NULL DEFAULT '',
    `rtime` datetime DEFAULT NULL,
    `state` int(11) NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 域名表
CREATE TABLE IF NOT EXISTS `wd_domain` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `uid` int(11) NOT NULL DEFAULT 0,
    `pid` int(11) NOT NULL DEFAULT 0,
    `gid` int(11) NOT NULL DEFAULT 0,
    `nid` int(11) NOT NULL DEFAULT 0,
    `domain` varchar(80) NOT NULL DEFAULT '',
    `count` int(11) NOT NULL DEFAULT 0,
    `inn` int(11) NOT NULL DEFAULT 0,
    `dcc` tinyint(1) NOT NULL DEFAULT 0,
    `note` varchar(100) NOT NULL DEFAULT '',
    `rtime` datetime DEFAULT NULL,
    `etime` bigint(20) NOT NULL DEFAULT 0,
    `state` int(11) NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    INDEX `idx_domain` (`uid`, `gid`, `domain`, `inn`, `state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='管理域名';

-- DNS记录表
CREATE TABLE IF NOT EXISTS `wd_record` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `did` int(11) NOT NULL DEFAULT 0,
    `uid` int(11) NOT NULL DEFAULT 0,
    `domain` varchar(80) NOT NULL DEFAULT '',
    `host` varchar(80) NOT NULL DEFAULT '',
    `qt` varchar(10) NOT NULL DEFAULT '',
    `val` varchar(100) NOT NULL DEFAULT '',
    `view` varchar(30) NOT NULL DEFAULT '',
    `ttl` int(11) NOT NULL DEFAULT 0,
    `pre` int(11) NOT NULL DEFAULT 0,
    `rtime` datetime DEFAULT NULL,
    `state` int(11) NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    INDEX `idx_record` (`did`, `uid`, `domain`, `host`, `qt`, `view`, `state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='存储DNS解析记录';

-- 反向解析表
CREATE TABLE IF NOT EXISTS `wd_ptr` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `uid` int(11) NOT NULL DEFAULT 0,
    `did` int(11) NOT NULL DEFAULT 0,
    `domain` varchar(255) NOT NULL DEFAULT '',
    `ip` varchar(255) NOT NULL DEFAULT '',
    `ttl` int(11) NOT NULL DEFAULT 0,
    `note` varchar(100) NOT NULL DEFAULT '',
    `rtime` datetime DEFAULT NULL,
    `state` int(11) NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    INDEX `idx_ptr` (`uid`, `domain`, `ip`, `state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 条件转发表
CREATE TABLE IF NOT EXISTS `wd_cfw` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `uid` int(11) NOT NULL DEFAULT 0,
    `domain` varchar(255) NOT NULL DEFAULT '',
    `ip` varchar(255) NOT NULL DEFAULT '',
    `note` varchar(100) NOT NULL DEFAULT '',
    `rtime` datetime DEFAULT NULL,
    `state` int(11) NOT NULL DEFAULT 0 COMMENT '1：暂时，空：正常',
    PRIMARY KEY (`id`),
    INDEX `idx_cfw` (`uid`, `domain`, `state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 转发设置表
CREATE TABLE IF NOT EXISTS `wd_nsg` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `name` varchar(255) NOT NULL DEFAULT '',
    `ns` varchar(255) NOT NULL DEFAULT '',
    `ttl` int(11) NOT NULL DEFAULT 0,
    `rtime` datetime DEFAULT NULL,
    `state` int(11) NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    INDEX `idx_nsg_state` (`state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 节点表
CREATE TABLE IF NOT EXISTS `wd_server` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `ip` varchar(15) NOT NULL DEFAULT '',
    `name` varchar(255) NOT NULL DEFAULT '',
    `dom` int(11) NOT NULL DEFAULT 0,
    `rec` int(11) NOT NULL DEFAULT 0,
    `qps` int(11) NOT NULL DEFAULT 0,
    `utime` varchar(255) NOT NULL DEFAULT '',
    `note` varchar(255) NOT NULL DEFAULT '',
    `rtime` datetime DEFAULT NULL,
    `state` int(11) NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 查询日志表
CREATE TABLE IF NOT EXISTS `wd_querylog` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `domain` varchar(255) NOT NULL DEFAULT '',
    `qtype` varchar(10) NOT NULL DEFAULT 'A',
    `client_ip` varchar(45) NOT NULL DEFAULT '',
    `forward` tinyint(1) NOT NULL DEFAULT 0,
    `qc` int(11) NOT NULL DEFAULT 1,
    `tn` bigint(20) NOT NULL DEFAULT 0,
    `rtime` datetime DEFAULT NULL,
    PRIMARY KEY (`id`),
    INDEX `idx_querylog_tn` (`tn`),
    INDEX `idx_querylog_domain` (`domain`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 操作日志表
CREATE TABLE IF NOT EXISTS `wd_optlog` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `uid` int(11) NOT NULL DEFAULT 0,
    `logt` int(11) NOT NULL DEFAULT 0,
    `ot` int(11) NOT NULL DEFAULT 0,
    `title` varchar(60) NOT NULL DEFAULT '',
    `msg` varchar(200) NOT NULL DEFAULT '',
    `ipaddr` varchar(32) NOT NULL DEFAULT '',
    `rtime` datetime DEFAULT NULL,
    `state` int(11) NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    INDEX `idx_optlog` (`uid`, `logt`, `state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 资源监控5分钟表
CREATE TABLE IF NOT EXISTS `wd_reslog5m` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `ip` varchar(15) NOT NULL DEFAULT '',
    `load1` double NOT NULL DEFAULT 0,
    `load2` double NOT NULL DEFAULT 0,
    `load3` double NOT NULL DEFAULT 0,
    `memu` double NOT NULL DEFAULT 0,
    `memf` double NOT NULL DEFAULT 0,
    `disku` double NOT NULL DEFAULT 0,
    `diskf` double NOT NULL DEFAULT 0,
    `inflow` double NOT NULL DEFAULT 0,
    `ouflow` double NOT NULL DEFAULT 0,
    `intra` double NOT NULL DEFAULT 0,
    `outra` double NOT NULL DEFAULT 0,
    `tn` bigint(20) NOT NULL DEFAULT 0,
    `rtime` datetime DEFAULT NULL,
    PRIMARY KEY (`id`),
    INDEX `idx_reslog5m_ip` (`ip`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 资源监控1小时表
CREATE TABLE IF NOT EXISTS `wd_reslog1h` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `ip` varchar(15) NOT NULL DEFAULT '',
    `load1` double NOT NULL DEFAULT 0,
    `load2` double NOT NULL DEFAULT 0,
    `load3` double NOT NULL DEFAULT 0,
    `memu` double NOT NULL DEFAULT 0,
    `memf` double NOT NULL DEFAULT 0,
    `disku` double NOT NULL DEFAULT 0,
    `diskf` double NOT NULL DEFAULT 0,
    `inflow` double NOT NULL DEFAULT 0,
    `ouflow` double NOT NULL DEFAULT 0,
    `intra` double NOT NULL DEFAULT 0,
    `outra` double NOT NULL DEFAULT 0,
    `tn` bigint(20) NOT NULL DEFAULT 0,
    `rtime` datetime DEFAULT NULL,
    PRIMARY KEY (`id`),
    INDEX `idx_reslog1h_ip` (`ip`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 资源监控1天表
CREATE TABLE IF NOT EXISTS `wd_reslog1d` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `ip` varchar(15) NOT NULL DEFAULT '',
    `load1` double NOT NULL DEFAULT 0,
    `load2` double NOT NULL DEFAULT 0,
    `load3` double NOT NULL DEFAULT 0,
    `memu` double NOT NULL DEFAULT 0,
    `memf` double NOT NULL DEFAULT 0,
    `disku` double NOT NULL DEFAULT 0,
    `diskf` double NOT NULL DEFAULT 0,
    `inflow` double NOT NULL DEFAULT 0,
    `ouflow` double NOT NULL DEFAULT 0,
    `intra` double NOT NULL DEFAULT 0,
    `outra` double NOT NULL DEFAULT 0,
    `tn` bigint(20) NOT NULL DEFAULT 0,
    `rtime` datetime DEFAULT NULL,
    PRIMARY KEY (`id`),
    INDEX `idx_reslog1d_ip` (`ip`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 系统配置表
CREATE TABLE IF NOT EXISTS `wd_sysconfig` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `ckey` varchar(50) NOT NULL DEFAULT '',
    `cval` text,
    `note` varchar(100) NOT NULL DEFAULT '',
    `rtime` datetime DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_ckey` (`ckey`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 分组表
CREATE TABLE IF NOT EXISTS `wd_group` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `uid` int(11) NOT NULL DEFAULT 0,
    `name` varchar(255) NOT NULL DEFAULT '',
    `rtime` datetime DEFAULT NULL,
    `state` int(11) NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    INDEX `idx_group` (`uid`, `state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 登录日志表
CREATE TABLE IF NOT EXISTS `wd_molog` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `mid` int(11) NOT NULL DEFAULT 0,
    `uid` int(11) NOT NULL DEFAULT 0,
    `url` varchar(255) NOT NULL DEFAULT '',
    `ip` varchar(15) NOT NULL DEFAULT '',
    `act` int(11) NOT NULL DEFAULT 0,
    `tn` varchar(255) NOT NULL DEFAULT '',
    `note` varchar(100) NOT NULL DEFAULT '',
    `rtime` datetime DEFAULT NULL,
    `state` int(11) NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    INDEX `idx_molog` (`mid`, `uid`, `ip`, `state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 插入默认管理员账号 (admin/admin, salt=85447c05)
INSERT INTO `wd_member` (`username`, `password`, `salt`, `rtime`, `state`) 
VALUES ('admin', '2a97516c3ba52242b97c500cb1f7c38b88ee7b9768eb7b5c86e3c8b8e8b8e8b8', '85447c05', NOW(), 0);

-- 插入默认转发设置
INSERT INTO `wd_nsg` (`name`, `ns`, `ttl`, `rtime`, `state`) 
VALUES ('default', '180.76.76.76,223.5.5.5,119.29.29.29', 60, NOW(), 0);

-- 插入默认节点
INSERT INTO `wd_server` (`ip`, `name`, `rtime`, `state`) 
VALUES ('127.0.0.1', 'local', NOW(), 0);

-- 插入默认系统配置
INSERT INTO `wd_sysconfig` (`ckey`, `cval`, `rtime`) VALUES 
('admin_name', '深圳科技', NOW()),
('admin_port', '8088', NOW()),
('login_ips', '', NOW()),
('cookie_time', '600', NOW()),
('main_ip', '', NOW()),
('enable_cfw', '0', NOW());
