package com.campus.common.security.config;

import cn.dev33.satoken.jwt.StpLogicJwtForSimple;
import cn.dev33.satoken.stp.StpInterface;
import cn.dev33.satoken.stp.StpLogic;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.context.annotation.Bean;

/**
 * Sa-Token 核心配置 — JWT 模式，密钥从 sa-token.jwt-secret-key 读取
 *
 * @author CampusQA Team
 */
@AutoConfiguration
public class SaTokenConfig {

    @Bean
    public StpLogic stpLogic() {
        return new StpLogicJwtForSimple();
    }

    @Bean
    public StpInterface stpInterface() {
        return new SaPermissionImpl();
    }
}
