package com.campus.common.log.aspect;

import cn.dev33.satoken.stp.StpUtil;
import cn.hutool.json.JSONUtil;
import com.campus.common.core.domain.R;
import com.campus.common.log.annotation.Log;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.multipart.MultipartFile;

import java.lang.reflect.Method;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.StringJoiner;

/**
 * 系统日志 AOP 切面 — 拦截 @Log 注解的方法，记录系统日志到 sys_oper_log 表
 */
@Aspect
@Component
public class LogAspect {

    private static final Logger log = LoggerFactory.getLogger(LogAspect.class);

    private static final int MAX_PARAM_LENGTH = 2000;
    private static final int MAX_RESULT_LENGTH = 2000;

    private static final String SQL_INSERT = """
            INSERT INTO sys_oper_log (title, business_type, method, request_method,
            oper_url, oper_ip, oper_param, json_result, status, error_msg,
            oper_time, oper_name, cost_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""";

    @Autowired
    private ApplicationContext applicationContext;

    @Around("@annotation(com.campus.common.log.annotation.Log)")
    public Object around(ProceedingJoinPoint point) throws Throwable {
        Instant start = Instant.now();
        Object result = null;
        Throwable exception = null;

        try {
            result = point.proceed();
            return result;
        } catch (Throwable e) {
            exception = e;
            throw e;
        } finally {
            recordLog(point, start, result, exception);
        }
    }

    private void recordLog(ProceedingJoinPoint point, Instant start, Object result, Throwable e) {
        try {
            MethodSignature signature = (MethodSignature) point.getSignature();
            Method method = signature.getMethod();
            Log logAnno = method.getAnnotation(Log.class);

            String title = logAnno.title();
            int businessType = logAnno.businessType();
            String methodName = point.getTarget().getClass().getName() + "." + method.getName();

            // 请求信息
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            String requestMethod = "";
            String operUrl = "";
            String operIp = "";
            if (attrs != null) {
                HttpServletRequest request = attrs.getRequest();
                requestMethod = request.getMethod();
                operUrl = request.getRequestURI();
                operIp = getIpAddr(request);
            }

            // 操作人
            String operName;
            try {
                operName = StpUtil.getLoginIdAsString();
            } catch (Exception ex) {
                operName = "anonymous";
            }

            // 耗时
            long costTime = Duration.between(start, Instant.now()).toMillis();

            // 状态 & 错误信息
            int status;
            String errorMsg = "";
            if (e != null) {
                status = 0;
                errorMsg = e.getMessage();
                if (errorMsg != null && errorMsg.length() > MAX_RESULT_LENGTH) {
                    errorMsg = errorMsg.substring(0, MAX_RESULT_LENGTH);
                }
            } else if (result instanceof R<?> r) {
                status = r.isSuccess() ? 1 : 0;
                if (!r.isSuccess()) {
                    errorMsg = r.getMsg() != null ? r.getMsg() : "";
                }
            } else {
                status = 1;
            }

            // 请求参数
            String operParam = "";
            if (logAnno.saveRequestParam()) {
                operParam = buildParams(point.getArgs());
            }

            // 响应结果
            String jsonResult = "";
            if (logAnno.saveResponseData() && e == null && result != null) {
                try {
                    jsonResult = JSONUtil.toJsonStr(result);
                    if (jsonResult.length() > MAX_RESULT_LENGTH) {
                        jsonResult = jsonResult.substring(0, MAX_RESULT_LENGTH);
                    }
                } catch (Exception ignored) {
                }
            }

            // 入库（运行时查找 JdbcTemplate，避免无数据源的模块启动报错）
            try {
                Object jt = applicationContext.getBean("jdbcTemplate");
                jt.getClass().getMethod("update", String.class, Object[].class)
                        .invoke(jt, SQL_INSERT, new Object[]{title, businessType, methodName,
                                requestMethod, operUrl, operIp, operParam, jsonResult,
                                status, errorMsg, LocalDateTime.now(), operName, costTime});
                return;
            } catch (Exception ignored) {
                // JdbcTemplate 不可用，降级 SLF4J
            }
            log.info("OPER_LOG title={} operName={} operUrl={} status={} costTime={}ms",
                    title, operName, operUrl, status, costTime);
        } catch (Exception ex) {
            log.warn("记录系统日志失败: {}", ex.getMessage());
        }
    }

    private String buildParams(Object[] args) {
        if (args == null || args.length == 0) return "";
        StringJoiner sj = new StringJoiner(", ");
        for (Object arg : args) {
            if (arg == null) continue;
            if (arg instanceof HttpServletRequest || arg instanceof HttpServletResponse
                    || arg instanceof MultipartFile) {
                continue;
            }
            try {
                String s = JSONUtil.toJsonStr(arg);
                sj.add(s);
            } catch (Exception ignored) {
            }
        }
        String result = sj.toString();
        if (result.length() > MAX_PARAM_LENGTH) {
            result = result.substring(0, MAX_PARAM_LENGTH);
        }
        return result;
    }

    private String getIpAddr(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        // IPv6 回环地址统一转为 127.0.0.1
        if ("0:0:0:0:0:0:0:1".equals(ip) || "::1".equals(ip)) {
            ip = "127.0.0.1";
        }
        return ip != null ? ip : "";
    }
}
