package com.campus.auth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.annotation.ComponentScan;

/**
 * 认证服务 — 登录 / 登出 / Token 签发
 *
 * @author CampusQA Team
 */
@EnableFeignClients(basePackages = "com.campus.api.system")
@EnableDiscoveryClient
@ComponentScan("com.campus")
@SpringBootApplication
public class CampusAuthApplication {

    public static void main(String[] args) {
        SpringApplication.run(CampusAuthApplication.class, args);
        System.out.println("\n========================================");
        System.out.println("  campus-auth 启动成功! 端口: 9210");
        System.out.println("========================================\n");
    }
}
