package com.campus.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.context.annotation.ComponentScan;

/**
 * 网关服务 — Spring Cloud Gateway 统一入口
 *
 * @author CampusQA Team
 */
@EnableDiscoveryClient
@ComponentScan({"com.campus.gateway", "com.campus.common.security"})
@SpringBootApplication
public class CampusGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(CampusGatewayApplication.class, args);
        System.out.println("\n========================================");
        System.out.println("  campus-gateway 启动成功! 端口: 19280");
        System.out.println("========================================\n");
    }
}
