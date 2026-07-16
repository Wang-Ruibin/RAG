package com.campus.knowledge;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.context.annotation.ComponentScan;

/**
 * 知识库管理服务
 *
 * @author CampusQA Team
 */
@EnableDiscoveryClient
@MapperScan("com.campus.knowledge.mapper")
@ComponentScan("com.campus")
@SpringBootApplication
public class CampusKnowledgeApplication {

    public static void main(String[] args) {
        SpringApplication.run(CampusKnowledgeApplication.class, args);
        System.out.println("\n========================================");
        System.out.println("  campus-knowledge 启动成功! 端口: 9202");
        System.out.println("========================================\n");
    }
}
