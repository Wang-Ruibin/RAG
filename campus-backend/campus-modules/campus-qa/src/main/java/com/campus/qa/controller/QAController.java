package com.campus.qa.controller;

import cn.dev33.satoken.stp.StpUtil;
import com.campus.api.knowledge.RemoteKnowledgeService;
import com.campus.common.core.domain.R;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;

import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * 校园问答接口 — 首页 RAG 对话
 *
 * 当前为占位实现（非流式），待 RAG 团队集成向量检索 + LLM 推理。
 * Feign 调用 Knowledge 服务做关键词检索。
 *
 * @author CampusQA Team
 */
@RestController
@RequestMapping("/qa")
public class QAController {

    private static final Logger log = LoggerFactory.getLogger(QAController.class);

    private final RemoteKnowledgeService remoteKnowledgeService;

    public QAController(RemoteKnowledgeService remoteKnowledgeService) {
        this.remoteKnowledgeService = remoteKnowledgeService;
    }

    /**
     * 校园知识问答（非流式）
     */
    @PostMapping("/ask")
    public R<Map<String, Object>> ask(@RequestBody Map<String, String> body) {
        String question = body.getOrDefault("question", "");
        if (question.isBlank()) {
            return R.fail("问题不能为空");
        }

        // 从知识库检索相关内容
        R<List<Map<String, Object>>> searchResult =
                remoteKnowledgeService.searchDocuments(question, 5);

        List<Map<String, Object>> sources = (searchResult != null && searchResult.isSuccess())
                ? searchResult.getData() : List.of();

        // 构建回答（占位 — 实际应由 LLM 基于检索结果生成）
        String answer = buildPlaceholderAnswer(question, sources);

        Map<String, Object> result = new java.util.HashMap<>();
        result.put("question", question);
        result.put("answer", answer);
        result.put("sources", sources);
        return R.ok(result);
    }

    /**
     * 流式问答接口（SSE — 供 RAG 团队对接 LLM 流式输出）
     */
    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<String> stream(@RequestParam String question) {
        // 占位：模拟流式输出
        String answer = "感谢你的提问！RAG 引擎正在集成中，届时将为你提供基于校园知识库的智能回答。";

        return Flux.fromArray(answer.split(""))
                .delayElements(Duration.ofMillis(30))
                .startWith("data: ")
                .concatWithValues("\n\n[DONE]");
    }

    /**
     * 对话历史（占位）
     */
    @GetMapping("/history")
    public R<List<Map<String, Object>>> history() {
        return R.ok(List.of());
    }

    // ==================== 私有方法 ====================

    private String buildPlaceholderAnswer(String question, List<Map<String, Object>> sources) {
        if (sources.isEmpty()) {
            return "抱歉，目前在知识库中未找到与「" + question + "」相关的信息。\n\n"
                    + "建议：\n"
                    + "1. 尝试使用不同的关键词搜索\n"
                    + "2. 联系管理员补充相关知识文档\n"
                    + "3. RAG 引擎集成后将提供更准确的语义搜索";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("根据知识库检索结果，为您找到以下相关信息：\n\n");
        for (int i = 0; i < sources.size(); i++) {
            Map<String, Object> doc = sources.get(i);
            sb.append("**").append(i + 1).append(". ").append(doc.get("title")).append("**\n");
            Object content = doc.get("content");
            if (content != null) {
                String text = content.toString();
                sb.append(text.substring(0, Math.min(200, text.length())));
                if (text.length() > 200) sb.append("...");
                sb.append("\n\n");
            }
        }
        sb.append("---\n*注：当前为关键词检索模式，RAG 语义检索引擎集成后将提供更精准的答案。*");
        return sb.toString();
    }
}
