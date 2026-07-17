package com.campus.common.datasource.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.BlockAttackInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import cn.dev33.satoken.stp.StpUtil;
import org.apache.ibatis.reflection.MetaObject;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.LocalDateTime;

/**
 * MyBatis-Plus 配置：分页插件 + 自动填充 + 防全表删改
 *
 * @author CampusQA Team
 */
@Configuration
public class MyBatisPlusConfig {

    /**
     * 分页插件 + 防全表更新删除
     */
    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        // 分页
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.MYSQL));
        // 防止全表更新或删除
        interceptor.addInnerInterceptor(new BlockAttackInnerInterceptor());
        return interceptor;
    }

    /**
     * 自动填充 createBy / createTime / updateBy / updateTime
     */
    @Bean
    public MetaObjectHandler metaObjectHandler() {
        return new MetaObjectHandler() {
            @Override
            public void insertFill(MetaObject metaObject) {
                String username = getCurrentUsername();
                this.setFieldValByName("createBy", username, metaObject);
                this.setFieldValByName("createTime", LocalDateTime.now(), metaObject);
                this.setFieldValByName("updateBy", username, metaObject);
                this.setFieldValByName("updateTime", LocalDateTime.now(), metaObject);
            }

            @Override
            public void updateFill(MetaObject metaObject) {
                this.setFieldValByName("updateBy", getCurrentUsername(), metaObject);
                this.setFieldValByName("updateTime", LocalDateTime.now(), metaObject);
            }

            private String getCurrentUsername() {
                try {
                    return StpUtil.getLoginIdAsString();
                } catch (Exception e) {
                    return "system";
                }
            }
        };
    }
}
