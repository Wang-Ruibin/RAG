package com.campus.knowledge.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.knowledge.domain.entity.KnowledgeDocument;

import java.util.List;
import java.util.Map;

public interface IKnowledgeDocumentService extends IService<KnowledgeDocument> {

    /** 关键词搜索 */
    List<Map<String, Object>> search(String keyword, int limit);

    /** 增加浏览次数 */
    void incrementViewCount(Long docId);
}
