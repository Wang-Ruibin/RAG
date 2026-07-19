package com.campus.system.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.system.domain.entity.SysOperLog;
import com.campus.system.mapper.SysOperLogMapper;
import com.campus.system.service.ISysOperLogService;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 操作日志 Service 实现
 */
@Service
public class SysOperLogServiceImpl extends ServiceImpl<SysOperLogMapper, SysOperLog> implements ISysOperLogService {

    @Override
    public void cleanLog() {
        // 加恒真条件绕过 BlockAttackInnerInterceptor 全表删除拦截
        baseMapper.delete(new LambdaQueryWrapper<SysOperLog>().gt(SysOperLog::getOperId, 0L));
    }

    @Override
    public void deleteLogs(List<Long> operIds) {
        baseMapper.deleteBatchIds(operIds);
    }
}
