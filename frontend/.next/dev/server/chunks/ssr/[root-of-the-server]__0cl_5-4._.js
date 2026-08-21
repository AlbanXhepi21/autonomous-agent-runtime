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
"[project]/components/artifact-panel.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ArtifactPanel",
    ()=>ArtifactPanel
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$markdown$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/markdown.tsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/explorer.ts [app-ssr] (ecmascript)");
"use client";
;
;
;
;
function ArtifactPanel({ runIds }) {
    const [items, setItems] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])([]);
    const [selected, setSelected] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const [content, setContent] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const runKey = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useMemo"])(()=>runIds.join(","), [
        runIds
    ]);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        const ids = runKey ? runKey.split(",") : [];
        void Promise.all(ids.map((runId)=>__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["explorerApi"].artifacts(runId))).then((groups)=>setItems(groups.flat())).catch(()=>setItems([]));
    }, [
        runKey
    ]);
    const preview = async (artifact)=>{
        setSelected(artifact);
        if (!artifact.media_type.startsWith("image/")) setContent((await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["explorerApi"].preview(artifact.artifact_id)).content);
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("aside", {
        className: "artifact-panel",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                children: "Generated Outputs"
            }, void 0, false, {
                fileName: "[project]/components/artifact-panel.tsx",
                lineNumber: 11,
                columnNumber: 44
            }, this),
            items.length === 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                children: "No generated outputs yet."
            }, void 0, false, {
                fileName: "[project]/components/artifact-panel.tsx",
                lineNumber: 11,
                columnNumber: 93
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                children: items.map((artifact)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                onClick: ()=>void preview(artifact),
                                children: artifact.name
                            }, void 0, false, {
                                fileName: "[project]/components/artifact-panel.tsx",
                                lineNumber: 11,
                                columnNumber: 186
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("a", {
                                href: __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["explorerApi"].downloadUrl(artifact.artifact_id),
                                children: "Download"
                            }, void 0, false, {
                                fileName: "[project]/components/artifact-panel.tsx",
                                lineNumber: 11,
                                columnNumber: 257
                            }, this)
                        ]
                    }, artifact.artifact_id, true, {
                        fileName: "[project]/components/artifact-panel.tsx",
                        lineNumber: 11,
                        columnNumber: 155
                    }, this))
            }, void 0, false, {
                fileName: "[project]/components/artifact-panel.tsx",
                lineNumber: 11,
                columnNumber: 126
            }, this),
            selected && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                        children: selected.name
                    }, void 0, false, {
                        fileName: "[project]/components/artifact-panel.tsx",
                        lineNumber: 11,
                        columnNumber: 359
                    }, this),
                    selected.media_type === "text/markdown" && content && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$markdown$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["SafeMarkdown"], {
                        content: content
                    }, void 0, false, {
                        fileName: "[project]/components/artifact-panel.tsx",
                        lineNumber: 11,
                        columnNumber: 438
                    }, this),
                    selected.media_type === "text/csv" && content && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("pre", {
                        children: content
                    }, void 0, false, {
                        fileName: "[project]/components/artifact-panel.tsx",
                        lineNumber: 11,
                        columnNumber: 523
                    }, this),
                    selected.media_type === "application/json" && content && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("pre", {
                        children: content
                    }, void 0, false, {
                        fileName: "[project]/components/artifact-panel.tsx",
                        lineNumber: 11,
                        columnNumber: 602
                    }, this),
                    selected.media_type.startsWith("image/") && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                        src: __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["explorerApi"].downloadUrl(selected.artifact_id),
                        alt: selected.name
                    }, void 0, false, {
                        fileName: "[project]/components/artifact-panel.tsx",
                        lineNumber: 11,
                        columnNumber: 668
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/artifact-panel.tsx",
                lineNumber: 11,
                columnNumber: 350
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/artifact-panel.tsx",
        lineNumber: 11,
        columnNumber: 10
    }, this);
}
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
"[project]/components/database-explorer.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "DatabaseExplorer",
    ()=>DatabaseExplorer
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/explorer.ts [app-ssr] (ecmascript)");
"use client";
;
;
;
function DatabaseExplorer() {
    const [tables, setTables] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])([]);
    const [selected, setSelected] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const [query, setQuery] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])("");
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        void __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["explorerApi"].tables().then((result)=>setTables(result.tables)).catch(()=>setError("Database schema is unavailable."));
    }, []);
    const choose = async (name)=>{
        try {
            setSelected(await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["explorerApi"].table(name));
        } catch  {
            setError("Table details are unavailable.");
        }
    };
    const shown = tables.filter((table)=>table.name.toLowerCase().includes(query.toLowerCase()));
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("aside", {
        className: "explorer-panel",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                children: [
                    "Database ",
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
                        children: [
                            tables.length,
                            " tables"
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/database-explorer.tsx",
                        lineNumber: 10,
                        columnNumber: 57
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/database-explorer.tsx",
                lineNumber: 10,
                columnNumber: 44
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                "aria-label": "Search database schema",
                value: query,
                onChange: (event)=>setQuery(event.target.value),
                placeholder: "Search schema"
            }, void 0, false, {
                fileName: "[project]/components/database-explorer.tsx",
                lineNumber: 10,
                columnNumber: 99
            }, this),
            error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                children: error
            }, void 0, false, {
                fileName: "[project]/components/database-explorer.tsx",
                lineNumber: 10,
                columnNumber: 247
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "schema-layout",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("nav", {
                        children: shown.map((table)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                onClick: ()=>void choose(table.name),
                                children: table.name
                            }, table.name, false, {
                                fileName: "[project]/components/database-explorer.tsx",
                                lineNumber: 10,
                                columnNumber: 320
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/components/database-explorer.tsx",
                        lineNumber: 10,
                        columnNumber: 293
                    }, this),
                    selected && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                                children: selected.table.name
                            }, void 0, false, {
                                fileName: "[project]/components/database-explorer.tsx",
                                lineNumber: 10,
                                columnNumber: 436
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                                children: selected.columns.map((column)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                                children: column.name
                                            }, void 0, false, {
                                                fileName: "[project]/components/database-explorer.tsx",
                                                lineNumber: 10,
                                                columnNumber: 526
                                            }, this),
                                            " ",
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                children: column.data_type
                                            }, void 0, false, {
                                                fileName: "[project]/components/database-explorer.tsx",
                                                lineNumber: 10,
                                                columnNumber: 557
                                            }, this),
                                            column.nullable ? "" : " · required"
                                        ]
                                    }, column.name, true, {
                                        fileName: "[project]/components/database-explorer.tsx",
                                        lineNumber: 10,
                                        columnNumber: 504
                                    }, this))
                            }, void 0, false, {
                                fileName: "[project]/components/database-explorer.tsx",
                                lineNumber: 10,
                                columnNumber: 466
                            }, this),
                            selected.foreign_keys.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Fragment"], {
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h4", {
                                        children: "Relationships"
                                    }, void 0, false, {
                                        fileName: "[project]/components/database-explorer.tsx",
                                        lineNumber: 10,
                                        columnNumber: 677
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                                        children: selected.foreign_keys.map((key, index)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                                children: [
                                                    key.column_name,
                                                    " → ",
                                                    key.referenced_table,
                                                    ".",
                                                    key.referenced_column
                                                ]
                                            }, index, true, {
                                                fileName: "[project]/components/database-explorer.tsx",
                                                lineNumber: 10,
                                                columnNumber: 746
                                            }, this))
                                    }, void 0, false, {
                                        fileName: "[project]/components/database-explorer.tsx",
                                        lineNumber: 10,
                                        columnNumber: 699
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/database-explorer.tsx",
                                lineNumber: 10,
                                columnNumber: 675
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/database-explorer.tsx",
                        lineNumber: 10,
                        columnNumber: 427
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/database-explorer.tsx",
                lineNumber: 10,
                columnNumber: 262
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/database-explorer.tsx",
        lineNumber: 10,
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
"[project]/components/memory-inspector.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "MemoryInspector",
    ()=>MemoryInspector
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-ssr] (ecmascript)");
"use client";
;
;
;
const labels = {
    working: "Working",
    episodic: "Episodic",
    long_term: "Semantic / long-term"
};
function MemoryInspector() {
    const [items, setItems] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])([]);
    const [type, setType] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])("");
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        void (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])(`/api/v1/memory${type ? `?memory_type=${type}` : ""}`).then(setItems).catch(()=>setError("Memory inspection is unavailable."));
    }, [
        type
    ]);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("aside", {
        className: "memory-panel",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                children: "Memory"
            }, void 0, false, {
                fileName: "[project]/components/memory-inspector.tsx",
                lineNumber: 11,
                columnNumber: 42
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "muted",
                children: "Retained information for future reasoning—not chat history or run trace."
            }, void 0, false, {
                fileName: "[project]/components/memory-inspector.tsx",
                lineNumber: 11,
                columnNumber: 57
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("select", {
                "aria-label": "Memory type",
                value: type,
                onChange: (event)=>setType(event.target.value),
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                        value: "",
                        children: "All types"
                    }, void 0, false, {
                        fileName: "[project]/components/memory-inspector.tsx",
                        lineNumber: 11,
                        columnNumber: 265
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                        value: "long_term",
                        children: "Semantic / long-term"
                    }, void 0, false, {
                        fileName: "[project]/components/memory-inspector.tsx",
                        lineNumber: 11,
                        columnNumber: 300
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                        value: "episodic",
                        children: "Episodic"
                    }, void 0, false, {
                        fileName: "[project]/components/memory-inspector.tsx",
                        lineNumber: 11,
                        columnNumber: 355
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                        value: "working",
                        children: "Working"
                    }, void 0, false, {
                        fileName: "[project]/components/memory-inspector.tsx",
                        lineNumber: 11,
                        columnNumber: 397
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/memory-inspector.tsx",
                lineNumber: 11,
                columnNumber: 154
            }, this),
            error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                children: error
            }, void 0, false, {
                fileName: "[project]/components/memory-inspector.tsx",
                lineNumber: 11,
                columnNumber: 456
            }, this),
            !error && items.length === 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "muted",
                children: "No retained memories."
            }, void 0, false, {
                fileName: "[project]/components/memory-inspector.tsx",
                lineNumber: 11,
                columnNumber: 504
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                children: items.map((memory)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                children: labels[memory.type]
                            }, void 0, false, {
                                fileName: "[project]/components/memory-inspector.tsx",
                                lineNumber: 11,
                                columnNumber: 598
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("time", {
                                children: new Date(memory.created_at).toLocaleString()
                            }, void 0, false, {
                                fileName: "[project]/components/memory-inspector.tsx",
                                lineNumber: 11,
                                columnNumber: 636
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                children: memory.content
                            }, void 0, false, {
                                fileName: "[project]/components/memory-inspector.tsx",
                                lineNumber: 11,
                                columnNumber: 695
                            }, this),
                            memory.run_id && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
                                children: [
                                    "Source run: ",
                                    memory.run_id
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/memory-inspector.tsx",
                                lineNumber: 11,
                                columnNumber: 736
                            }, this),
                            memory.session_id && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
                                children: [
                                    "Session: ",
                                    memory.session_id
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/memory-inspector.tsx",
                                lineNumber: 11,
                                columnNumber: 801
                            }, this),
                            typeof memory.metadata.category === "string" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
                                children: [
                                    "Category: ",
                                    memory.metadata.category
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/memory-inspector.tsx",
                                lineNumber: 11,
                                columnNumber: 894
                            }, this)
                        ]
                    }, memory.id, true, {
                        fileName: "[project]/components/memory-inspector.tsx",
                        lineNumber: 11,
                        columnNumber: 578
                    }, this))
            }, void 0, false, {
                fileName: "[project]/components/memory-inspector.tsx",
                lineNumber: 11,
                columnNumber: 551
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/memory-inspector.tsx",
        lineNumber: 11,
        columnNumber: 10
    }, this);
}
}),
"[project]/features/workbench/run-analysis.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "RunAnalysis",
    ()=>RunAnalysis
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
"use client";
;
;
const FILTERS = [
    [
        "all",
        "All"
    ],
    [
        "sql",
        "SQL"
    ],
    [
        "tools",
        "Tools"
    ],
    [
        "artifacts",
        "Artifacts"
    ],
    [
        "errors",
        "Errors"
    ]
];
function eventFilter(event, filter) {
    if (filter === "all") return true;
    if (filter === "sql") return event.type.startsWith("sql.");
    if (filter === "tools") return event.type.startsWith("tool.") || event.type.startsWith("schema.") || event.type.startsWith("python.") || event.type.startsWith("delegation.");
    if (filter === "artifacts") return event.type.includes("artifact") || event.type.includes("chart") || event.type.includes("report");
    return event.type.includes("failed") || event.type.includes("rejected") || event.type.startsWith("security.");
}
function eventText(event) {
    const data = event.data;
    if (event.type === "skill.loaded") return `Data analysis skill loaded${typeof data.skill === "string" ? `: ${data.skill}` : ""}`;
    if (event.type === "schema.table_described") return `Inspected ${(Array.isArray(data.tables) ? data.tables : []).join(", ") || "table"}`;
    if (event.type === "schema.tables_listed") return "Inspected available tables";
    if (event.type === "sql.query_started") return `Running ${queryLabel(event)}`;
    if (event.type === "sql.query_completed") return `${queryLabel(event)} completed`;
    if (event.type === "sql.query_failed") return `${queryLabel(event)} failed`;
    if (event.type === "sql.query_rejected") return `${queryLabel(event)} rejected by SQL safety policy`;
    if (event.type === "python.analysis_started") return "Python analysis started";
    if (event.type === "python.analysis_completed") return "Python analysis completed";
    if (event.type === "artifact.created" || event.type === "chart.created" || event.type === "report.created") return "Artifact created";
    if (event.type === "delegation.started") return `Delegated analysis${typeof data.agent_name === "string" ? ` → ${data.agent_name}` : ""}`;
    if (event.type === "delegation.completed") return "Delegated analysis completed";
    if (event.type === "security.policy_evaluated") return data.decision === "deny" ? "Tool denied by capability policy" : "Security policy evaluated";
    if (event.type === "tool.completed") return `${toolName(data)} completed`;
    if (event.type === "tool.failed") return `${toolName(data)} failed`;
    if (event.type === "run.completed") return "Analysis completed";
    if (event.type === "run.failed") return "Analysis failed";
    return event.type.replace(/[._]/g, " ");
}
function queryLabel(event) {
    return `Query #${typeof event.data.query_id === "string" ? event.data.query_id.replace(/^query_?0*/, "") || event.data.query_id : "?"}`;
}
function toolName(data) {
    return typeof data.tool_name === "string" ? data.tool_name.replaceAll("_", " ") : "Tool";
}
function isFailure(event) {
    return event.type.includes("failed") || event.type.includes("rejected") || event.type === "security.policy_evaluated" && event.data.decision === "deny";
}
function metric(value) {
    return value === null || value === undefined ? "—" : value;
}
function Metrics({ metrics }) {
    if (!metrics) return null;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dl", {
        className: "run-metrics",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Duration"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 43
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: metric(metrics.total_duration_ms === null ? null : `${metrics.total_duration_ms}ms`)
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 60
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 47,
                columnNumber: 38
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Iterations"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 166
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: metrics.iterations
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 185
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 47,
                columnNumber: 161
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "SQL queries"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 225
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: metrics.database_query_count
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 245
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 47,
                columnNumber: 220
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Tool calls"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 295
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: metrics.tool_calls
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 314
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 47,
                columnNumber: 290
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Tokens"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 354
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: metric(metrics.total_tokens)
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 369
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 47,
                columnNumber: 349
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Estimated cost"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 419
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: metrics.estimated_cost === null ? "—" : `$${metrics.estimated_cost.toFixed(4)}`
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 47,
                        columnNumber: 442
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 47,
                columnNumber: 414
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/features/workbench/run-analysis.tsx",
        lineNumber: 47,
        columnNumber: 10
    }, this);
}
function RunAnalysis({ run, events, loading }) {
    const [open, setOpen] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(false);
    const [filter, setFilter] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])("all");
    const visible = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useMemo"])(()=>events.filter((event)=>eventFilter(event, filter)), [
        events,
        filter
    ]);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
        className: "run-analysis",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                className: "analysis-toggle",
                onClick: ()=>setOpen((value)=>!value),
                "aria-expanded": open,
                children: [
                    open ? "⌄" : "›",
                    " View analysis"
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 53,
                columnNumber: 44
            }, this),
            open && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "analysis-body",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "analysis-heading",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "eyebrow",
                                        children: "ANALYSIS RUN"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                        lineNumber: 53,
                                        columnNumber: 264
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                        children: run?.status === "failed" ? "Failed" : run?.status === "running" ? "Running" : "Completed"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                        lineNumber: 53,
                                        columnNumber: 309
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                lineNumber: 53,
                                columnNumber: 259
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(Metrics, {
                                metrics: run?.metrics
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                lineNumber: 53,
                                columnNumber: 423
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 53,
                        columnNumber: 225
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "trace-filters",
                        children: FILTERS.map(([value, label])=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                className: filter === value ? "active" : "",
                                onClick: ()=>setFilter(value),
                                children: label
                            }, value, false, {
                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                lineNumber: 53,
                                columnNumber: 527
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 53,
                        columnNumber: 463
                    }, this),
                    loading && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "trace-empty",
                        children: "Loading structured trace…"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 53,
                        columnNumber: 661
                    }, this),
                    !loading && visible.length === 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "trace-empty",
                        children: "No public trace events are available for this run."
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 53,
                        columnNumber: 755
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("ol", {
                        className: "trace-events",
                        children: visible.map((event)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                className: isFailure(event) ? "failure" : "",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "trace-icon",
                                        children: isFailure(event) ? "⚠" : event.type.endsWith("started") ? "●" : "✓"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                        lineNumber: 53,
                                        columnNumber: 955
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                                children: eventText(event)
                                            }, void 0, false, {
                                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                                lineNumber: 53,
                                                columnNumber: 1065
                                            }, this),
                                            event.type.startsWith("sql.") && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "query-details",
                                                children: [
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        children: [
                                                            "Status: ",
                                                            event.type === "sql.query_completed" ? "Completed" : event.type === "sql.query_failed" ? "Failed" : event.type === "sql.query_rejected" ? "Rejected" : "Running"
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                                        lineNumber: 53,
                                                        columnNumber: 1165
                                                    }, this),
                                                    typeof event.data.duration_ms === "number" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        children: [
                                                            "Duration: ",
                                                            event.data.duration_ms,
                                                            "ms"
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                                        lineNumber: 53,
                                                        columnNumber: 1395
                                                    }, this),
                                                    typeof event.data.row_count === "number" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        children: [
                                                            "Rows: ",
                                                            event.data.row_count
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                                        lineNumber: 53,
                                                        columnNumber: 1490
                                                    }, this),
                                                    Array.isArray(event.data.referenced_tables) && event.data.referenced_tables.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        children: [
                                                            "Tables: ",
                                                            event.data.referenced_tables.join(", ")
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                                        lineNumber: 53,
                                                        columnNumber: 1623
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("details", {
                                                        children: [
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("summary", {
                                                                children: "SQL"
                                                            }, void 0, false, {
                                                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                                                lineNumber: 53,
                                                                columnNumber: 1695
                                                            }, this),
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                                children: "SQL is not retained or exposed for this run."
                                                            }, void 0, false, {
                                                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                                                lineNumber: 53,
                                                                columnNumber: 1717
                                                            }, this)
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                                        lineNumber: 53,
                                                        columnNumber: 1686
                                                    }, this)
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                                lineNumber: 53,
                                                columnNumber: 1134
                                            }, this),
                                            typeof event.data.error === "string" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                className: "trace-reason",
                                                children: [
                                                    "Reason: ",
                                                    event.data.error
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                                lineNumber: 53,
                                                columnNumber: 1826
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                        lineNumber: 53,
                                        columnNumber: 1060
                                    }, this)
                                ]
                            }, event.id, true, {
                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                lineNumber: 53,
                                columnNumber: 890
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 53,
                        columnNumber: 837
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 53,
                columnNumber: 194
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/features/workbench/run-analysis.tsx",
        lineNumber: 53,
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
var __TURBOPACK__imported__module__$5b$project$5d2f$features$2f$workbench$2f$run$2d$analysis$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/features/workbench/run-analysis.tsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$artifact$2d$panel$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/artifact-panel.tsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$database$2d$explorer$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/database-explorer.tsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$memory$2d$inspector$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/memory-inspector.tsx [app-ssr] (ecmascript)");
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
    const [runs, setRuns] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])({});
    const [eventsByRun, setEventsByRun] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])({});
    const [loadingTraces, setLoadingTraces] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])({});
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
            const historicalRuns = conversation.runs ?? [];
            setConversationId(conversation.id);
            setMessages(conversation.messages.map((message)=>({
                    role: message.role,
                    content: message.content,
                    run_id: message.run_id
                })));
            setRuns(Object.fromEntries(historicalRuns.map((run)=>[
                    run.run_id,
                    run
                ])));
            setLoadingTraces(Object.fromEntries(historicalRuns.map((run)=>[
                    run.run_id,
                    true
                ])));
            const histories = await Promise.all(historicalRuns.map(async (run)=>[
                    run.run_id,
                    await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["analyticsApi"].getEvents(run.run_id).then((result)=>result.items).catch(()=>[])
                ]));
            setEventsByRun(Object.fromEntries(histories));
            setLoadingTraces({});
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
        setRuns((current)=>({
                ...current,
                [runId]: {
                    run_id: run.run_id,
                    status: run.status,
                    created_at: run.created_at,
                    started_at: run.started_at,
                    completed_at: run.finished_at,
                    error: run.error,
                    metrics: run.metrics
                }
            }));
        if (run.status === "completed" && run.final_response) setMessages((current)=>[
                ...current,
                {
                    role: "assistant",
                    content: run.final_response,
                    run_id: runId
                }
            ]);
        else if (run.status === "waiting_for_approval") setError("The analyst is waiting for approval before making a protected change. No answer has been produced yet.");
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
            setRuns((current)=>({
                    ...current,
                    [created.run_id]: {
                        run_id: created.run_id,
                        status: "running",
                        created_at: "",
                        started_at: null,
                        completed_at: null,
                        error: null,
                        metrics: null
                    }
                }));
            setEventsByRun((current)=>({
                    ...current,
                    [created.run_id]: []
                }));
            source.current = __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["analyticsApi"].connect(created.run_id, (event)=>{
                setEventsByRun((current)=>({
                        ...current,
                        [created.run_id]: current[created.run_id]?.some((existing)=>existing.id === event.id) ? current[created.run_id] : [
                            ...current[created.run_id] ?? [],
                            event
                        ]
                    }));
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
        setRuns({});
        setEventsByRun({});
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
                                lineNumber: 96,
                                columnNumber: 12
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                                children: "AI Data Analyst"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 96,
                                columnNumber: 54
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 96,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        className: "new-conversation",
                        onClick: ()=>void newConversation(),
                        children: "＋ New conversation"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 97,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                children: "CONVERSATIONS"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 98,
                                columnNumber: 16
                            }, this),
                            historyError && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "muted",
                                role: "alert",
                                children: historyError
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 98,
                                columnNumber: 53
                            }, this),
                            !historyError && conversations.length === 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "muted",
                                children: "No saved conversations yet."
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 98,
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
                                                lineNumber: 99,
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
                                                        lineNumber: 99,
                                                        columnNumber: 254
                                                    }, this))
                                            }, void 0, false, {
                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                lineNumber: 99,
                                                columnNumber: 184
                                            }, this)
                                        ]
                                    }, group.label, true, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 99,
                                        columnNumber: 108
                                    }, this))
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 99,
                                columnNumber: 9
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 98,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$artifact$2d$panel$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ArtifactPanel"], {
                        runIds: Object.keys(runs)
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 101,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$database$2d$explorer$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["DatabaseExplorer"], {}, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 102,
                        columnNumber: 7
                    }, this),
                    process.env.NEXT_PUBLIC_DEVELOPER_MODE === "true" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$memory$2d$inspector$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["MemoryInspector"], {}, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 103,
                        columnNumber: 61
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/workbench.tsx",
                lineNumber: 95,
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
                                        lineNumber: 105,
                                        columnNumber: 52
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                                        children: "AI Data Analyst"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 105,
                                        columnNumber: 101
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 105,
                                columnNumber: 47
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "connection",
                                children: "● Backend connected"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 105,
                                columnNumber: 131
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 105,
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
                                        lineNumber: 106,
                                        columnNumber: 112
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                        children: "Try investigating revenue changes, customer behavior, conversion, or operational performance."
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 106,
                                        columnNumber: 151
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 106,
                                columnNumber: 89
                            }, this),
                            messages.map((message, index)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "message-with-analysis",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("article", {
                                            className: `message ${message.role}`,
                                            "data-run-id": message.run_id ?? undefined,
                                            children: message.role === "assistant" ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$markdown$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["SafeMarkdown"], {
                                                content: message.content
                                            }, void 0, false, {
                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                lineNumber: 106,
                                                columnNumber: 500
                                            }, this) : message.content
                                        }, void 0, false, {
                                            fileName: "[project]/features/workbench/workbench.tsx",
                                            lineNumber: 106,
                                            columnNumber: 379
                                        }, this),
                                        message.role === "assistant" && message.run_id && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$features$2f$workbench$2f$run$2d$analysis$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["RunAnalysis"], {
                                            run: runs[message.run_id],
                                            events: eventsByRun[message.run_id] ?? [],
                                            loading: loadingTraces[message.run_id]
                                        }, void 0, false, {
                                            fileName: "[project]/features/workbench/workbench.tsx",
                                            lineNumber: 106,
                                            columnNumber: 622
                                        }, this)
                                    ]
                                }, `${message.run_id ?? "message"}-${index}`, true, {
                                    fileName: "[project]/features/workbench/workbench.tsx",
                                    lineNumber: 106,
                                    columnNumber: 292
                                }, this)),
                            status && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "progress",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "spinner"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 106,
                                        columnNumber: 793
                                    }, this),
                                    status
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 106,
                                columnNumber: 767
                            }, this),
                            error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "error",
                                role: "alert",
                                children: error
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 106,
                                columnNumber: 846
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 106,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$chat$2d$composer$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ChatComposer"], {
                        onSubmit: submit,
                        disabled: Boolean(status)
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 107,
                        columnNumber: 7
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/workbench.tsx",
                lineNumber: 105,
                columnNumber: 5
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/features/workbench/workbench.tsx",
        lineNumber: 94,
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
"[project]/lib/api/explorer.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "explorerApi",
    ()=>explorerApi
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-ssr] (ecmascript)");
;
const explorerApi = {
    artifacts: (runId)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])(`/artifacts${runId ? `?run_id=${encodeURIComponent(runId)}` : ""}`),
    preview: (id)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])(`/artifacts/${id}/preview`),
    downloadUrl: (id)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["eventUrl"])(`/artifacts/${id}`),
    tables: ()=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])("/api/v1/schema/tables"),
    search: (query)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])(`/api/v1/schema/search?q=${encodeURIComponent(query)}`),
    table: (name)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["request"])(`/api/v1/schema/tables/${encodeURIComponent(name)}`)
};
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__0cl_5-4._.js.map