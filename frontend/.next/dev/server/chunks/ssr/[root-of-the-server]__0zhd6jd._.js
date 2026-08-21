module.exports = [
"[externals]/node:path [external] (node:path, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("node:path", () => require("node:path"));

module.exports = mod;
}),
"[externals]/node:path [external] (node:path, cjs) <export default as minpath>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "minpath",
    ()=>__TURBOPACK__imported__module__$5b$externals$5d2f$node$3a$path__$5b$external$5d$__$28$node$3a$path$2c$__cjs$29$__["default"]
]);
var __TURBOPACK__imported__module__$5b$externals$5d2f$node$3a$path__$5b$external$5d$__$28$node$3a$path$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/node:path [external] (node:path, cjs)");
}),
"[externals]/node:process [external] (node:process, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("node:process", () => require("node:process"));

module.exports = mod;
}),
"[externals]/node:process [external] (node:process, cjs) <export default as minproc>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "minproc",
    ()=>__TURBOPACK__imported__module__$5b$externals$5d2f$node$3a$process__$5b$external$5d$__$28$node$3a$process$2c$__cjs$29$__["default"]
]);
var __TURBOPACK__imported__module__$5b$externals$5d2f$node$3a$process__$5b$external$5d$__$28$node$3a$process$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/node:process [external] (node:process, cjs)");
}),
"[externals]/node:url [external] (node:url, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("node:url", () => require("node:url"));

module.exports = mod;
}),
"[externals]/node:url [external] (node:url, cjs) <export fileURLToPath as urlToPath>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "urlToPath",
    ()=>__TURBOPACK__imported__module__$5b$externals$5d2f$node$3a$url__$5b$external$5d$__$28$node$3a$url$2c$__cjs$29$__["fileURLToPath"]
]);
var __TURBOPACK__imported__module__$5b$externals$5d2f$node$3a$url__$5b$external$5d$__$28$node$3a$url$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/node:url [external] (node:url, cjs)");
}),
"[externals]/os [external] (os, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("os", () => require("os"));

module.exports = mod;
}),
"[externals]/tty [external] (tty, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("tty", () => require("tty"));

module.exports = mod;
}),
"[externals]/util [external] (util, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("util", () => require("util"));

module.exports = mod;
}),
"[project]/components/chat-composer.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ChatComposer",
    ()=>ChatComposer
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
"use client";
;
;
function ChatComposer({ onSubmit, disabled }) {
    const [value, setValue] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])("");
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
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
        className: "composer",
        onSubmit: submit,
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
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
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
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
}),
"[project]/components/markdown.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "SafeMarkdown",
    ()=>SafeMarkdown
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$markdown$2f$lib$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__Markdown__as__default$3e$__ = __turbopack_context__.i("[project]/node_modules/react-markdown/lib/index.js [app-ssr] (ecmascript) <export Markdown as default>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$remark$2d$gfm$2f$lib$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/remark-gfm/lib/index.js [app-ssr] (ecmascript)");
;
;
;
function SqlCode({ children }) {
    const pieces = children.split(/(\b(?:SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|GROUP|ORDER|BY|AS|ON|AND|OR|COUNT|SUM|AVG|LIMIT|WITH)\b)/gi);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("code", {
        className: "sql-code",
        children: pieces.map((piece, index)=>/^(select|from|where|join|left|right|inner|group|order|by|as|on|and|or|count|sum|avg|limit|with)$/i.test(piece) ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
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
function SafeMarkdown({ content }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$markdown$2f$lib$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__Markdown__as__default$3e$__["default"], {
        remarkPlugins: [
            __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$remark$2d$gfm$2f$lib$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"]
        ],
        components: {
            code ({ className, children }) {
                const value = String(children).replace(/\n$/, "");
                return className?.includes("language-sql") ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(SqlCode, {
                    children: value
                }, void 0, false, {
                    fileName: "[project]/components/markdown.tsx",
                    lineNumber: 13,
                    columnNumber: 52
                }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("code", {
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
}),
"[project]/features/workbench/status.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
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
}),
"[project]/features/workbench/workbench.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "Workbench",
    ()=>Workbench
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$chat$2d$composer$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/chat-composer.tsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$markdown$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/markdown.tsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/analytics.ts [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$conversations$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/conversations.ts [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$features$2f$workbench$2f$status$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/features/workbench/status.ts [app-ssr] (ecmascript)");
"use client";
;
;
;
;
;
;
;
;
function groupConversations(conversations) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const recent = [];
    const previous = [];
    conversations.forEach((conversation)=>{
        const updatedAt = new Date(conversation.updated_at);
        (Number.isNaN(updatedAt.getTime()) || updatedAt >= today ? recent : previous).push(conversation);
    });
    return [
        {
            label: "Today",
            items: recent
        },
        {
            label: "Previous",
            items: previous
        }
    ].filter((group)=>group.items.length > 0);
}
function Workbench() {
    const [messages, setMessages] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])([]);
    const [status, setStatus] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const [conversations, setConversations] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])([]);
    const [conversationId, setConversationId] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const [historyError, setHistoryError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const source = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRef"])(null);
    const terminalRun = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRef"])(null);
    const finishing = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRef"])(false);
    const conversationGroups = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useMemo"])(()=>groupConversations(conversations), [
        conversations
    ]);
    const loadConversations = async ()=>{
        try {
            const page = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$conversations$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["conversationsApi"].list();
            setConversations(page.items);
            setHistoryError(null);
        } catch  {
            setHistoryError("Conversation history could not be loaded.");
        }
    };
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        const timer = window.setTimeout(()=>{
            void loadConversations();
        }, 0);
        return ()=>window.clearTimeout(timer);
    }, []);
    const switchConversation = async (id)=>{
        source.current?.close();
        terminalRun.current = null;
        finishing.current = false;
        setStatus(null);
        setError(null);
        try {
            const conversation = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$conversations$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["conversationsApi"].get(id);
            setConversationId(conversation.id);
            setMessages(conversation.messages.map((message)=>({
                    role: message.role,
                    content: message.content,
                    run_id: message.run_id
                })));
        } catch  {
            setHistoryError("Conversation could not be loaded.");
        }
    };
    const finish = async (runId)=>{
        if (finishing.current) return;
        finishing.current = true;
        let run;
        for(let attempt = 0; attempt < 8; attempt += 1){
            run = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["analyticsApi"].getRun(runId);
            if (run.status !== "running") break;
            await new Promise((resolve)=>window.setTimeout(resolve, 100));
        }
        if (!run) throw new Error("The run result was unavailable.");
        if (run.status === "completed" && run.final_response) setMessages((current)=>[
                ...current,
                {
                    role: "assistant",
                    content: run.final_response,
                    run_id: runId
                }
            ]);
        else setError(run.error ?? "The analyst run ended without an answer.");
        setStatus(null);
        source.current?.close();
        source.current = null;
        void loadConversations();
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
                    content: message,
                    run_id: null
                }
            ]);
        try {
            const created = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["analyticsApi"].createRun({
                message,
                ...conversationId ? {
                    conversation_id: conversationId
                } : {}
            });
            setConversationId(created.conversation_id);
            void loadConversations();
            source.current = __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["analyticsApi"].connect(created.run_id, (event)=>{
                setStatus((0, __TURBOPACK__imported__module__$5b$project$5d2f$features$2f$workbench$2f$status$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["statusFromEvent"])(event));
                if (event.type === "run.completed") {
                    terminalRun.current = created.run_id;
                    void finish(created.run_id);
                }
                if (event.type === "run.failed") {
                    terminalRun.current = created.run_id;
                    setError(typeof event.data.error === "string" ? event.data.error : "The analyst run failed.");
                    setStatus(null);
                    source.current?.close();
                    void loadConversations();
                }
            }, ()=>{
                if (terminalRun.current === created.run_id) return;
                setError("The progress stream disconnected. Checking the run status…");
                void finish(created.run_id).catch(()=>setStatus(null));
            });
        } catch (cause) {
            setStatus(null);
            setError(cause instanceof __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"] ? cause.message : "Unable to start the analyst run.");
        }
    };
    const newConversation = async ()=>{
        source.current?.close();
        terminalRun.current = null;
        finishing.current = false;
        setMessages([]);
        setStatus(null);
        setError(null);
        try {
            const conversation = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$conversations$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["conversationsApi"].create();
            setConversationId(conversation.id);
            setConversations((current)=>[
                    conversation,
                    ...current
                ]);
        } catch  {
            setHistoryError("A new conversation could not be created.");
        }
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("main", {
        className: "workbench",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("aside", {
                className: "sidebar",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "eyebrow",
                                children: "WORKBENCH"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 78,
                                columnNumber: 12
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                                children: "AI Data Analyst"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 78,
                                columnNumber: 54
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 78,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        className: "new-conversation",
                        onClick: ()=>void newConversation(),
                        children: "＋ New conversation"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 79,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                children: "CONVERSATIONS"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 80,
                                columnNumber: 16
                            }, this),
                            historyError && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "muted",
                                role: "alert",
                                children: historyError
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 80,
                                columnNumber: 53
                            }, this),
                            !historyError && conversations.length === 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "muted",
                                children: "No saved conversations yet."
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 80,
                                columnNumber: 160
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("nav", {
                                className: "conversation-groups",
                                "aria-label": "Conversations",
                                children: conversationGroups.map((group)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "conversation-group",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                                                children: group.label
                                            }, void 0, false, {
                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                lineNumber: 81,
                                                columnNumber: 162
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "conversation-list",
                                                children: group.items.map((conversation)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                        className: conversation.id === conversationId ? "active" : "",
                                                        onClick: ()=>void switchConversation(conversation.id),
                                                        title: conversation.title,
                                                        children: conversation.title
                                                    }, conversation.id, false, {
                                                        fileName: "[project]/features/workbench/workbench.tsx",
                                                        lineNumber: 81,
                                                        columnNumber: 254
                                                    }, this))
                                            }, void 0, false, {
                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                lineNumber: 81,
                                                columnNumber: 184
                                            }, this)
                                        ]
                                    }, group.label, true, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 81,
                                        columnNumber: 108
                                    }, this))
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 81,
                                columnNumber: 9
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 80,
                        columnNumber: 7
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/workbench.tsx",
                lineNumber: 77,
                columnNumber: 5
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "conversation",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "eyebrow",
                                        children: "ANALYSIS SESSION"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 84,
                                        columnNumber: 52
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                                        children: "AI Data Analyst"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 84,
                                        columnNumber: 101
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 84,
                                columnNumber: 47
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "connection",
                                children: "● Backend connected"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 84,
                                columnNumber: 131
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 84,
                        columnNumber: 39
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "messages",
                        "aria-live": "polite",
                        children: [
                            messages.length === 0 && !status && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "empty",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                                        children: "Ask a question about your data"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 85,
                                        columnNumber: 112
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                        children: "Try investigating revenue changes, customer behavior, conversion, or operational performance."
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 85,
                                        columnNumber: 151
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 85,
                                columnNumber: 89
                            }, this),
                            messages.map((message, index)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("article", {
                                    className: `message ${message.role}`,
                                    "data-run-id": message.run_id ?? undefined,
                                    children: message.role === "assistant" ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$markdown$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["SafeMarkdown"], {
                                        content: message.content
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 85,
                                        columnNumber: 461
                                    }, this) : message.content
                                }, `${message.run_id ?? "message"}-${index}`, false, {
                                    fileName: "[project]/features/workbench/workbench.tsx",
                                    lineNumber: 85,
                                    columnNumber: 292
                                }, this)),
                            status && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "progress",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "spinner"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 85,
                                        columnNumber: 571
                                    }, this),
                                    status
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 85,
                                columnNumber: 545
                            }, this),
                            error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "error",
                                role: "alert",
                                children: error
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 85,
                                columnNumber: 624
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 85,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$chat$2d$composer$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ChatComposer"], {
                        onSubmit: submit,
                        disabled: Boolean(status)
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 86,
                        columnNumber: 7
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/workbench.tsx",
                lineNumber: 84,
                columnNumber: 5
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/features/workbench/workbench.tsx",
        lineNumber: 76,
        columnNumber: 10
    }, this);
}
}),
"[project]/lib/api/analytics.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "analyticsApi",
    ()=>analyticsApi
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-ssr] (ecmascript)");
;
const analyticsApi = {
    createRun: (payload)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])("/api/v1/analytics/runs", {
            method: "POST",
            body: JSON.stringify(payload)
        }),
    getRun: (runId)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])(`/api/v1/analytics/runs/${runId}`),
    getEvents: (runId)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])(`/api/v1/analytics/runs/${runId}/events/history`),
    streamUrl: (runId)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["eventUrl"])(`/api/v1/analytics/runs/${runId}/events`),
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
}),
"[project]/lib/api/client.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ApiError",
    ()=>ApiError,
    "eventUrl",
    ()=>eventUrl,
    "request",
    ()=>request
]);
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
}),
"[project]/lib/api/conversations.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "conversationsApi",
    ()=>conversationsApi
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-ssr] (ecmascript)");
;
const conversationsApi = {
    create: (title = "New conversation")=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])("/api/v1/conversations", {
            method: "POST",
            body: JSON.stringify({
                title
            })
        }),
    list: (limit = 30, offset = 0)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])(`/api/v1/conversations?limit=${limit}&offset=${offset}`),
    get: (id, messageLimit = 100, messageOffset = 0)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])(`/api/v1/conversations/${id}?message_limit=${messageLimit}&message_offset=${messageOffset}`),
    remove: (id)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])(`/api/v1/conversations/${id}`, {
            method: "DELETE"
        })
};
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__0zhd6jd._.js.map