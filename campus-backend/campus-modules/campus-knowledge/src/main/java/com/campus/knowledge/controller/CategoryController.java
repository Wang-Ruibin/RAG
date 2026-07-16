package com.campus.knowledge.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.campus.common.core.domain.R;
import com.campus.common.log.annotation.Log;
import com.campus.knowledge.domain.entity.KnowledgeCategory;
import com.campus.knowledge.service.IKnowledgeCategoryService;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 知识分类管理
 */
@RestController
@RequestMapping("/knowledge/category")
public class CategoryController {

    private final IKnowledgeCategoryService categoryService;

    public CategoryController(IKnowledgeCategoryService categoryService) {
        this.categoryService = categoryService;
    }

    @GetMapping("/tree")
    public R<List<KnowledgeCategory>> tree() {
        return R.ok(categoryService.getTree());
    }

    /**
     * 分类列表（带文档计数）
     */
    @SaCheckPermission("knowledge:category:list")
    @GetMapping("/list")
    public R<List<Map<String, Object>>> list() {
        List<KnowledgeCategory> categories = categoryService.getTree();
        List<Map<String, Object>> result = categories.stream().map(c -> {
            Map<String, Object> m = new HashMap<>();
            m.put("categoryId", c.getCategoryId());
            m.put("categoryName", c.getCategoryName());
            m.put("categoryKey", c.getCategoryKey());
            m.put("sortOrder", c.getSortOrder());
            m.put("icon", c.getIcon());
            m.put("docCount", categoryService.getDocCount(c.getCategoryId()));
            return m;
        }).toList();
        return R.ok(result);
    }

    @SaCheckPermission("knowledge:category:add")
    @Log(title = "新增知识分类", businessType = 1)
    @PostMapping
    public R<Void> add(@RequestBody KnowledgeCategory category) {
        categoryService.save(category);
        return R.ok();
    }

    @SaCheckPermission("knowledge:category:edit")
    @Log(title = "修改知识分类", businessType = 2)
    @PutMapping
    public R<Void> edit(@RequestBody KnowledgeCategory category) {
        categoryService.updateById(category);
        return R.ok();
    }

    @SaCheckPermission("knowledge:category:remove")
    @Log(title = "删除知识分类", businessType = 3)
    @DeleteMapping("/{categoryIds}")
    public R<Void> remove(@PathVariable("categoryIds") List<Long> categoryIds) {
        categoryService.removeByIds(categoryIds);
        return R.ok();
    }
}
