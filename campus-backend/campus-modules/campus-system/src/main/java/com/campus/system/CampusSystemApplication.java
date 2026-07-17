package com.campus.system;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.annotation.ComponentScan;

/**
 * 系统管理服务
 *
 * @author CampusQA Team
 */
@EnableFeignClients
@EnableDiscoveryClient
@MapperScan("com.campus.system.mapper")
@ComponentScan("com.campus")
@SpringBootApplication
public class CampusSystemApplication {

    public static void main(String[] args) {
        SpringApplication.run(CampusSystemApplication.class, args);
        System.out.println("\n========================================");
        System.out.println("  campus-system 启动成功! 端口: 9201");
        System.out.println("========================================\n");
    }
}
