package com.campus.qa;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;

/**
 * RAG 问答服务
 *
 * @author CampusQA Team
 */
@EnableFeignClients(basePackages = "com.campus.api.knowledge")
@EnableDiscoveryClient
@SpringBootApplication
public class CampusQAApplication {

    public static void main(String[] args) {
        SpringApplication.run(CampusQAApplication.class, args);
        System.out.println("\n========================================");
        System.out.println("  campus-qa 启动成功! 端口: 9203");
        System.out.println("========================================\n");
    }
}
