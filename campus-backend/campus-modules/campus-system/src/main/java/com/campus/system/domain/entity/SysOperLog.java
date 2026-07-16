package com.campus.system.domain.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 操作日志实体
 */
@TableName("sys_oper_log")
public class SysOperLog implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long operId;
    private String title;
    private Integer businessType;
    private String method;
    private String requestMethod;
    private String operUrl;
    private String operIp;
    private String operParam;
    private String jsonResult;
    private Integer status;
    private String errorMsg;
    private LocalDateTime operTime;
    private String operName;
    private Long costTime;

    public Long getOperId() { return operId; }
    public void setOperId(Long operId) { this.operId = operId; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public Integer getBusinessType() { return businessType; }
    public void setBusinessType(Integer businessType) { this.businessType = businessType; }

    public String getMethod() { return method; }
    public void setMethod(String method) { this.method = method; }

    public String getRequestMethod() { return requestMethod; }
    public void setRequestMethod(String requestMethod) { this.requestMethod = requestMethod; }

    public String getOperUrl() { return operUrl; }
    public void setOperUrl(String operUrl) { this.operUrl = operUrl; }

    public String getOperIp() { return operIp; }
    public void setOperIp(String operIp) { this.operIp = operIp; }

    public String getOperParam() { return operParam; }
    public void setOperParam(String operParam) { this.operParam = operParam; }

    public String getJsonResult() { return jsonResult; }
    public void setJsonResult(String jsonResult) { this.jsonResult = jsonResult; }

    public Integer getStatus() { return status; }
    public void setStatus(Integer status) { this.status = status; }

    public String getErrorMsg() { return errorMsg; }
    public void setErrorMsg(String errorMsg) { this.errorMsg = errorMsg; }

    public LocalDateTime getOperTime() { return operTime; }
    public void setOperTime(LocalDateTime operTime) { this.operTime = operTime; }

    public String getOperName() { return operName; }
    public void setOperName(String operName) { this.operName = operName; }

    public Long getCostTime() { return costTime; }
    public void setCostTime(Long costTime) { this.costTime = costTime; }
}
