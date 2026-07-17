package com.campus.auth.controller;

import cn.dev33.satoken.stp.SaTokenInfo;
import cn.hutool.captcha.CaptchaUtil;
import cn.hutool.captcha.LineCaptcha;
import com.campus.auth.service.LoginService;
import com.campus.common.core.domain.R;
import com.campus.common.core.exception.ServiceException;
import com.campus.common.log.annotation.Log;
import jakarta.validation.Valid;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/**
 * 认证接口 — 登录 / 登出 / 注册 / 验证码
 */
@RestController
@RequestMapping("/auth")
public class AuthController {

    private final LoginService loginService;
    private final StringRedisTemplate redisTemplate;

    public AuthController(LoginService loginService, StringRedisTemplate redisTemplate) {
        this.loginService = loginService;
        this.redisTemplate = redisTemplate;
    }

    /** 生成验证码 */
    @GetMapping("/captcha")
    public R<Map<String, Object>> captcha() {
        LineCaptcha captcha = CaptchaUtil.createLineCaptcha(120, 40, 4, 80);
        String uuid = UUID.randomUUID().toString().replace("-", "");
        String code = captcha.getCode();
        redisTemplate.opsForValue().set("captcha:" + uuid, code, 2, TimeUnit.MINUTES);
        Map<String, Object> result = new HashMap<>();
        result.put("uuid", uuid);
        result.put("img", captcha.getImageBase64Data());
        return R.ok(result);
    }

    /** 验证码校验 */
    private void validateCaptcha(String uuid, String code) {
        if (uuid == null || code == null) {
            throw new ServiceException("请输入验证码");
        }
        String cached = redisTemplate.opsForValue().get("captcha:" + uuid);
        if (cached == null) {
            throw new ServiceException("验证码已过期");
        }
        if (!cached.equalsIgnoreCase(code)) {
            throw new ServiceException("验证码错误");
        }
        redisTemplate.delete("captcha:" + uuid);
    }

    /** 登录 */
    @Log(title = "用户登录", businessType = 4)
    @PostMapping("/login")
    public R<Map<String, Object>> login(@Valid @RequestBody LoginBody body) {
        validateCaptcha(body.getUuid(), body.getCode());
        SaTokenInfo tokenInfo = loginService.login(body.getUsername(), body.getPassword());
        Map<String, Object> result = new HashMap<>();
        result.put("token", tokenInfo.getTokenValue());
        result.put("tokenName", tokenInfo.getTokenName());
        return R.ok(result, "登录成功");
    }

    /** 注册 */
    @Log(title = "用户注册", businessType = 1)
    @PostMapping("/register")
    public R<Void> register(@Valid @RequestBody RegisterBody body) {
        validateCaptcha(body.getUuid(), body.getCode());
        loginService.register(body.getUsername(), body.getPassword(),
                body.getNickName(), body.getEmail(), body.getPhone());
        return R.ok(null, "注册成功");
    }

    /** 登出 */
    @PostMapping("/logout")
    public R<Void> logout() {
        loginService.logout();
        return R.ok();
    }

    /** 获取当前用户信息 */
    @GetMapping("/getInfo")
    public R<Map<String, Object>> getInfo() {
        return R.ok(loginService.getCurrentUserInfo());
    }
}
