package com.campus.system.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.system.domain.entity.SysOperLog;

import java.util.List;

/**
 * 操作日志 Service 接口
 */
public interface ISysOperLogService extends IService<SysOperLog> {

    /** 清空日志 */
    void cleanLog();

    /** 批量删除 */
    void deleteLogs(List<Long> operIds);
}
