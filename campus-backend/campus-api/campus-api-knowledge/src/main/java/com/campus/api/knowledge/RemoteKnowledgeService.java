package com.campus.api.knowledge;

import com.campus.common.core.domain.R;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;
import java.util.Map;

/**
 * Knowledge 知识库服务 Feign 接口 — QA 模块通过此接口检索知识
 *
 * @author CampusQA Team
 */
@FeignClient(name = "campus-knowledge", path = "/knowledge")
public interface RemoteKnowledgeService {

    /**
     * 关键词搜索文档（供 RAG 模块调用）
     */
    @GetMapping("/document/search")
    R<List<Map<String, Object>>> searchDocuments(@RequestParam("keyword") String keyword,
                                                  @RequestParam(value = "limit", defaultValue = "5") int limit);
}
