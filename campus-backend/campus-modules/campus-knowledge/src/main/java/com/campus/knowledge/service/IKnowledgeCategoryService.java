package com.campus.knowledge.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.knowledge.domain.entity.KnowledgeCategory;

import java.util.List;

public interface IKnowledgeCategoryService extends IService<KnowledgeCategory> {

    List<KnowledgeCategory> getTree();

    long getDocCount(Long categoryId);
}
