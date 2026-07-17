package com.campus.common.core.web;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import java.io.Serializable;
import java.util.List;

/**
 * 分页查询参数 + 分页结果封装
 *
 * @author CampusQA Team
 */
public class PageQuery implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 当前页码 */
    private Long pageNum = 1L;

    /** 每页条数 */
    private Long pageSize = 10L;

    /** 排序列 */
    private String orderByColumn;

    /** 排序方向 asc/desc */
    private String isAsc = "desc";

    public Long getPageNum() { return pageNum; }
    public void setPageNum(Long pageNum) { this.pageNum = pageNum; }

    public Long getPageSize() { return pageSize; }
    public void setPageSize(Long pageSize) { this.pageSize = pageSize; }

    public String getOrderByColumn() { return orderByColumn; }
    public void setOrderByColumn(String orderByColumn) { this.orderByColumn = orderByColumn; }

    public String getIsAsc() { return isAsc; }
    public void setIsAsc(String isAsc) { this.isAsc = isAsc; }

    /**
     * 构建 MyBatis-Plus 分页对象
     */
    public <T> Page<T> buildPage() {
        Page<T> page = new Page<>(this.pageNum, this.pageSize);
        page.setOptimizeCountSql(false);
        return page;
    }

    // ==================== 分页结果封装 ====================

    /**
     * 将 MyBatis-Plus 分页结果封装为前端友好的格式
     */
    public static <T> PageResult<T> result(IPage<T> page) {
        return new PageResult<>(page.getRecords(), page.getTotal(), page.getCurrent(), page.getSize());
    }

    /**
     * 分页结果 VO
     */
    public static class PageResult<T> implements Serializable {
        private static final long serialVersionUID = 1L;

        private final List<T> rows;
        private final long total;
        private final long pageNum;
        private final long pageSize;

        public PageResult(List<T> rows, long total, long pageNum, long pageSize) {
            this.rows = rows;
            this.total = total;
            this.pageNum = pageNum;
            this.pageSize = pageSize;
        }

        public List<T> getRows() { return rows; }
        public long getTotal() { return total; }
        public long getPageNum() { return pageNum; }
        public long getPageSize() { return pageSize; }
    }
}
