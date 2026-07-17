package com.campus.system.domain.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.campus.common.core.domain.BaseEntity;

/**
 * 用户实体
 *
 * @author CampusQA Team
 */
@TableName("sys_user")
public class SysUser extends BaseEntity {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long userId;
    private String userName;
    private String nickName;
    private String password;
    private String email;
    private String phone;
    private String sex;
    private String avatar;
    private String status;
    private String loginIp;
    private String loginDate;

    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }

    public String getUserName() { return userName; }
    public void setUserName(String userName) { this.userName = userName; }

    public String getNickName() { return nickName; }
    public void setNickName(String nickName) { this.nickName = nickName; }

    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }

    public String getSex() { return sex; }
    public void setSex(String sex) { this.sex = sex; }

    public String getAvatar() { return avatar; }
    public void setAvatar(String avatar) { this.avatar = avatar; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getLoginIp() { return loginIp; }
    public void setLoginIp(String loginIp) { this.loginIp = loginIp; }

    public String getLoginDate() { return loginDate; }
    public void setLoginDate(String loginDate) { this.loginDate = loginDate; }
}
