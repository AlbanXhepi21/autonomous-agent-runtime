(globalThis["TURBOPACK"] || (globalThis["TURBOPACK"] = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/components/chat-composer.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ChatComposer",
    ()=>ChatComposer
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
function ChatComposer({ onSubmit, disabled }) {
    _s();
    const [value, setValue] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const submit = (event)=>{
        event?.preventDefault();
        const message = value.trim();
        if (!message || disabled) return;
        onSubmit(message);
        setValue("");
    };
    const onKeyDown = (event)=>{
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
        }
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
        className: "composer",
        onSubmit: submit,
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                "aria-label": "Ask about your data",
                placeholder: "Ask about your data…",
                value: value,
                disabled: disabled,
                onChange: (event)=>setValue(event.target.value),
                onKeyDown: onKeyDown,
                rows: 1
            }, void 0, false, {
                fileName: "[project]/components/chat-composer.tsx",
                lineNumber: 10,
                columnNumber: 5
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                type: "submit",
                disabled: disabled || !value.trim(),
                children: disabled ? "Analyzing" : "Analyze"
            }, void 0, false, {
                fileName: "[project]/components/chat-composer.tsx",
                lineNumber: 11,
                columnNumber: 5
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/chat-composer.tsx",
        lineNumber: 9,
        columnNumber: 10
    }, this);
}
_s(ChatComposer, "dBtK6I2q1m3rcfzPBa0nrbv/iCI=");
_c = ChatComposer;
var _c;
__turbopack_context__.k.register(_c, "ChatComposer");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/markdown.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "SafeMarkdown",
    ()=>SafeMarkdown
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$markdown$2f$lib$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__Markdown__as__default$3e$__ = __turbopack_context__.i("[project]/node_modules/react-markdown/lib/index.js [app-client] (ecmascript) <export Markdown as default>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$remark$2d$gfm$2f$lib$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/remark-gfm/lib/index.js [app-client] (ecmascript)");
;
;
;
function SqlCode({ children }) {
    const pieces = children.split(/(\b(?:SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|GROUP|ORDER|BY|AS|ON|AND|OR|COUNT|SUM|AVG|LIMIT|WITH)\b)/gi);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("code", {
        className: "sql-code",
        children: pieces.map((piece, index)=>/^(select|from|where|join|left|right|inner|group|order|by|as|on|and|or|count|sum|avg|limit|with)$/i.test(piece) ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                className: "sql-keyword",
                children: piece
            }, index, false, {
                fileName: "[project]/components/markdown.tsx",
                lineNumber: 6,
                columnNumber: 181
            }, this) : piece)
    }, void 0, false, {
        fileName: "[project]/components/markdown.tsx",
        lineNumber: 6,
        columnNumber: 10
    }, this);
}
_c = SqlCode;
function SafeMarkdown({ content }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$markdown$2f$lib$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__Markdown__as__default$3e$__["default"], {
        remarkPlugins: [
            __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$remark$2d$gfm$2f$lib$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"]
        ],
        components: {
            code ({ className, children }) {
                const value = String(children).replace(/\n$/, "");
                return className?.includes("language-sql") ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(SqlCode, {
                    children: value
                }, void 0, false, {
                    fileName: "[project]/components/markdown.tsx",
                    lineNumber: 13,
                    columnNumber: 52
                }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("code", {
                    className: className,
                    children: children
                }, void 0, false, {
                    fileName: "[project]/components/markdown.tsx",
                    lineNumber: 13,
                    columnNumber: 81
                }, this);
            }
        },
        children: content
    }, void 0, false, {
        fileName: "[project]/components/markdown.tsx",
        lineNumber: 10,
        columnNumber: 10
    }, this);
}
_c1 = SafeMarkdown;
var _c, _c1;
__turbopack_context__.k.register(_c, "SqlCode");
__turbopack_context__.k.register(_c1, "SafeMarkdown");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/features/workbench/status.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "statusFromEvent",
    ()=>statusFromEvent
]);
function statusFromEvent(event) {
    if (event.type.startsWith("schema.")) return "Inspecting database…";
    if (event.type.startsWith("sql.query")) return event.type === "sql.query_completed" ? "Comparing results…" : "Running query…";
    if (event.type.startsWith("python.")) return "Analyzing results…";
    if (event.type === "agent.completed") return "Preparing answer…";
    return "Analyzing…";
}
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/features/workbench/workbench.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "Workbench",
    ()=>Workbench
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$chat$2d$composer$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/chat-composer.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$markdown$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/markdown.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/analytics.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$features$2f$workbench$2f$status$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/features/workbench/status.ts [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
;
;
;
;
function Workbench() {
    _s();
    const [messages, setMessages] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const [status, setStatus] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const source = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const terminalRun = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const finishing = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(false);
    const finish = async (runId)=>{
        if (finishing.current) return;
        finishing.current = true;
        let run;
        // The completion trace event is recorded just before the UI run coordinator
        // stores its final response. Briefly retry so SSE never races the status API.
        for(let attempt = 0; attempt < 8; attempt += 1){
            run = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["analyticsApi"].getRun(runId);
            if (run.status !== "running") break;
            await new Promise((resolve)=>window.setTimeout(resolve, 100));
        }
        if (!run) throw new Error("The run result was unavailable.");
        if (run.status === "completed" && run.final_response) setMessages((current)=>[
                ...current,
                {
                    role: "assistant",
                    content: run.final_response
                }
            ]);
        else setError(run.error ?? "The analyst run ended without an answer.");
        setStatus(null);
        source.current?.close();
        source.current = null;
    };
    const submit = async (message)=>{
        terminalRun.current = null;
        finishing.current = false;
        setError(null);
        setStatus("Analyzing…");
        setMessages((current)=>[
                ...current,
                {
                    role: "user",
                    content: message
                }
            ]);
        try {
            const created = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["analyticsApi"].createRun({
                message
            });
            source.current = __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["analyticsApi"].connect(created.run_id, (event)=>{
                setStatus((0, __TURBOPACK__imported__module__$5b$project$5d2f$features$2f$workbench$2f$status$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["statusFromEvent"])(event));
                if (event.type === "run.completed") {
                    terminalRun.current = created.run_id;
                    void finish(created.run_id);
                }
                if (event.type === "run.failed") {
                    terminalRun.current = created.run_id;
                    setError(typeof event.data.error === "string" ? event.data.error : "The analyst run failed.");
                    setStatus(null);
                    source.current?.close();
                }
            }, ()=>{
                // EventSource reports a completed server-closed SSE connection as an error.
                if (terminalRun.current === created.run_id) return;
                setError("The progress stream disconnected. Checking the run status…");
                void finish(created.run_id).catch(()=>setStatus(null));
            });
        } catch (cause) {
            setStatus(null);
            setError(cause instanceof __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ApiError"] ? cause.message : "Unable to start the analyst run.");
        }
    };
    const newConversation = ()=>{
        source.current?.close();
        terminalRun.current = null;
        finishing.current = false;
        setMessages([]);
        setStatus(null);
        setError(null);
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("main", {
        className: "workbench",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("aside", {
                className: "sidebar",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "eyebrow",
                                children: "WORKBENCH"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 55,
                                columnNumber: 37
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                                children: "AI Data Analyst"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 55,
                                columnNumber: 79
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 55,
                        columnNumber: 32
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        className: "new-conversation",
                        onClick: newConversation,
                        children: "＋ New conversation"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 55,
                        columnNumber: 109
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                children: "RECENT"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 55,
                                columnNumber: 208
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "muted",
                                children: "History will appear here when it is available."
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 55,
                                columnNumber: 221
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 55,
                        columnNumber: 199
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/workbench.tsx",
                lineNumber: 55,
                columnNumber: 5
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "conversation",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "eyebrow",
                                        children: "ANALYSIS SESSION"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 56,
                                        columnNumber: 52
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                                        children: "AI Data Analyst"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 56,
                                        columnNumber: 101
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 56,
                                columnNumber: 47
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "connection",
                                children: "● Backend connected"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 56,
                                columnNumber: 131
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 56,
                        columnNumber: 39
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "messages",
                        "aria-live": "polite",
                        children: [
                            messages.length === 0 && !status && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "empty",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                                        children: "Ask a question about your data"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 57,
                                        columnNumber: 112
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                        children: "Try investigating revenue changes, customer behavior, conversion, or operational performance."
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 57,
                                        columnNumber: 151
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 57,
                                columnNumber: 89
                            }, this),
                            messages.map((message, index)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("article", {
                                    className: `message ${message.role}`,
                                    children: message.role === "assistant" ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$markdown$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["SafeMarkdown"], {
                                        content: message.content
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 58,
                                        columnNumber: 132
                                    }, this) : message.content
                                }, index, false, {
                                    fileName: "[project]/features/workbench/workbench.tsx",
                                    lineNumber: 58,
                                    columnNumber: 41
                                }, this)),
                            status && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "progress",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "spinner"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 59,
                                        columnNumber: 44
                                    }, this),
                                    status
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 59,
                                columnNumber: 18
                            }, this),
                            error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "error",
                                role: "alert",
                                children: error
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 60,
                                columnNumber: 17
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 57,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$chat$2d$composer$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ChatComposer"], {
                        onSubmit: submit,
                        disabled: Boolean(status)
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 61,
                        columnNumber: 7
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/workbench.tsx",
                lineNumber: 56,
                columnNumber: 5
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/features/workbench/workbench.tsx",
        lineNumber: 54,
        columnNumber: 10
    }, this);
}
_s(Workbench, "8xrTWsFznZmUAXSTlx22lEL//V0=");
_c = Workbench;
var _c;
__turbopack_context__.k.register(_c, "Workbench");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/lib/api/analytics.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "analyticsApi",
    ()=>analyticsApi
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-client] (ecmascript)");
;
const analyticsApi = {
    createRun: (payload)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])("/api/v1/analytics/runs", {
            method: "POST",
            body: JSON.stringify(payload)
        }),
    getRun: (runId)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/api/v1/analytics/runs/${runId}`),
    streamUrl: (runId)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["eventUrl"])(`/api/v1/analytics/runs/${runId}/events`),
    connect (runId, onEvent, onError) {
        const source = new EventSource(analyticsApi.streamUrl(runId));
        const eventTypes = [
            "run.started",
            "run.completed",
            "run.failed",
            "agent.started",
            "agent.completed",
            "skill.loaded",
            "schema.tables_listed",
            "schema.table_described",
            "sql.query_started",
            "sql.query_completed",
            "sql.query_failed",
            "sql.query_rejected",
            "python.analysis_started",
            "python.analysis_completed",
            "artifact.created",
            "chart.created",
            "report.created",
            "delegation.started",
            "delegation.completed"
        ];
        for (const type of eventTypes)source.addEventListener(type, (message)=>onEvent(JSON.parse(message.data)));
        source.onerror = onError;
        return source;
    }
};
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/lib/api/client.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ApiError",
    ()=>ApiError,
    "eventUrl",
    ()=>eventUrl,
    "request",
    ()=>request
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
class ApiError extends Error {
    status;
    constructor(message, status){
        super(message), this.status = status;
        this.name = "ApiError";
    }
}
const baseUrl = ()=>("TURBOPACK compile-time value", "http://localhost:8000") ?? "http://localhost:8000";
async function request(path, init) {
    let response;
    try {
        response = await fetch(`${baseUrl()}${path}`, {
            ...init,
            headers: {
                "Content-Type": "application/json",
                ...init?.headers
            }
        });
    } catch  {
        throw new ApiError("The analyst backend is unavailable. Check that FastAPI is running.");
    }
    if (!response.ok) {
        const payload = await response.json().catch(()=>null);
        const detail = typeof payload?.detail === "string" ? payload.detail : payload?.detail?.message;
        throw new ApiError(detail ?? "The analyst request could not be completed.", response.status);
    }
    if (response.status === 204) return undefined;
    return response.json();
}
const eventUrl = (path)=>`${baseUrl()}${path}`;
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=_0xivkfn._.js.map