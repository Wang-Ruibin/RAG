package com.campus.common.swagger.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Knife4j API 文档配置
 *
 * @author CampusQA Team
 */
@Configuration
public class SwaggerConfig {

    @Bean
    public OpenAPI campusOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("CampusQA - 校园知识问答助手 API")
                        .description("河海大学校园知识问答系统接口文档")
                        .version("1.0.0")
                        .contact(new Contact()
                                .name("CampusQA Team")));
    }
}
