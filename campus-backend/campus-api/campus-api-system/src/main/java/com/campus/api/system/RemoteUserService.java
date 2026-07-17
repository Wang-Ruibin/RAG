package com.campus.api.system;

import com.campus.api.system.model.LoginUserVO;
import com.campus.common.core.domain.R;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;

/**
 * System 用户服务 Feign 接口 — Auth 模块通过此接口查询用户信息
 *
 * @author CampusQA Team
 */
@FeignClient(name = "campus-system", path = "/system/user")
public interface RemoteUserService {

    /**
     * 根据用户名查询用户信息（用于登录校验）
     */
    @GetMapping("/info/{userName}")
    R<LoginUserVO> getUserByName(@PathVariable("userName") String userName);

    /**
     * 获取用户权限列表
     */
    @GetMapping("/perms/{userName}")
    R<List<String>> getUserPermissions(@PathVariable("userName") String userName);

    /**
     * 获取用户角色列表
     */
    @GetMapping("/roles/{userName}")
    R<List<String>> getUserRoles(@PathVariable("userName") String userName);

    /**
     * 密码验证（BCrypt 比对）
     */
    @GetMapping("/validate/{userName}")
    R<Boolean> validatePassword(@PathVariable("userName") String userName,
                                @RequestParam("password") String password);

    /**
     * 用户注册
     */
    @PostMapping("/register")
    R<Void> registerUser(@RequestParam("username") String username,
                          @RequestParam("password") String password,
                          @RequestParam("nickName") String nickName,
                          @RequestParam(value = "email", required = false) String email,
                          @RequestParam(value = "phone", required = false) String phone);
}
