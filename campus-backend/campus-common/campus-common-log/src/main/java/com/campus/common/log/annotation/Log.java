package com.campus.common.log.annotation;

import java.lang.annotation.*;

/**
 * 系统日志注解 — 标注在 Controller 方法上自动记录系统日志
 *
 * @author CampusQA Team
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Log {

    /** 操作模块 */
    String title() default "";

    /** 业务类型: 0=其它 1=新增 2=修改 3=删除 4=查询 */
    int businessType() default 0;

    /** 是否保存请求参数 */
    boolean saveRequestParam() default true;

    /** 是否保存响应结果 */
    boolean saveResponseData() default true;
}
