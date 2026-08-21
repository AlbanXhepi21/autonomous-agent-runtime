(globalThis["TURBOPACK"] || (globalThis["TURBOPACK"] = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/components/approval-card.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ApprovalCard",
    ()=>ApprovalCard
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
"use client";
;
function ApprovalCard({ approval, busy, onApprove, onReject }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
        className: "approval-card",
        "aria-label": "Approval required",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                children: "Approval required"
            }, void 0, false, {
                fileName: "[project]/components/approval-card.tsx",
                lineNumber: 7,
                columnNumber: 5
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                children: approval.reason
            }, void 0, false, {
                fileName: "[project]/components/approval-card.tsx",
                lineNumber: 7,
                columnNumber: 39
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dl", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Agent"
                    }, void 0, false, {
                        fileName: "[project]/components/approval-card.tsx",
                        lineNumber: 8,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: approval.agent_name
                    }, void 0, false, {
                        fileName: "[project]/components/approval-card.tsx",
                        lineNumber: 8,
                        columnNumber: 23
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Action"
                    }, void 0, false, {
                        fileName: "[project]/components/approval-card.tsx",
                        lineNumber: 8,
                        columnNumber: 53
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: approval.tool_name
                    }, void 0, false, {
                        fileName: "[project]/components/approval-card.tsx",
                        lineNumber: 8,
                        columnNumber: 68
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Capability"
                    }, void 0, false, {
                        fileName: "[project]/components/approval-card.tsx",
                        lineNumber: 8,
                        columnNumber: 97
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: approval.capability
                    }, void 0, false, {
                        fileName: "[project]/components/approval-card.tsx",
                        lineNumber: 8,
                        columnNumber: 116
                    }, this),
                    approval.resource && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                                children: "Resource"
                            }, void 0, false, {
                                fileName: "[project]/components/approval-card.tsx",
                                lineNumber: 8,
                                columnNumber: 170
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                                children: approval.resource
                            }, void 0, false, {
                                fileName: "[project]/components/approval-card.tsx",
                                lineNumber: 8,
                                columnNumber: 187
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/approval-card.tsx",
                        lineNumber: 8,
                        columnNumber: 168
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/approval-card.tsx",
                lineNumber: 8,
                columnNumber: 5
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "muted",
                children: "Only a safe summary is shown; executable arguments remain protected."
            }, void 0, false, {
                fileName: "[project]/components/approval-card.tsx",
                lineNumber: 9,
                columnNumber: 5
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        onClick: onApprove,
                        disabled: busy,
                        children: "Approve"
                    }, void 0, false, {
                        fileName: "[project]/components/approval-card.tsx",
                        lineNumber: 10,
                        columnNumber: 10
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        onClick: onReject,
                        disabled: busy,
                        children: "Reject"
                    }, void 0, false, {
                        fileName: "[project]/components/approval-card.tsx",
                        lineNumber: 10,
                        columnNumber: 70
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/approval-card.tsx",
                lineNumber: 10,
                columnNumber: 5
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/approval-card.tsx",
        lineNumber: 6,
        columnNumber: 10
    }, this);
}
_c = ApprovalCard;
var _c;
__turbopack_context__.k.register(_c, "ApprovalCard");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/artifact-panel.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ArtifactPanel",
    ()=>ArtifactPanel
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$markdown$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/markdown.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/explorer.ts [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
;
function ArtifactPanel({ runIds, refreshKey }) {
    _s();
    const [items, setItems] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const [selected, setSelected] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [content, setContent] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const runKey = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "ArtifactPanel.useMemo[runKey]": ()=>runIds.join(",")
    }["ArtifactPanel.useMemo[runKey]"], [
        runIds
    ]);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "ArtifactPanel.useEffect": ()=>{
            const ids = runKey ? runKey.split(",") : [];
            void Promise.all(ids.map({
                "ArtifactPanel.useEffect": (runId)=>__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["explorerApi"].artifacts(runId)
            }["ArtifactPanel.useEffect"])).then({
                "ArtifactPanel.useEffect": (groups)=>setItems(groups.flat())
            }["ArtifactPanel.useEffect"]).catch({
                "ArtifactPanel.useEffect": ()=>setItems([])
            }["ArtifactPanel.useEffect"]);
        }
    }["ArtifactPanel.useEffect"], [
        runKey,
        refreshKey
    ]);
    const preview = async (artifact)=>{
        setSelected(artifact);
        if (!artifact.media_type.startsWith("image/")) setContent((await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["explorerApi"].preview(artifact.artifact_id)).content);
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("aside", {
        className: "artifact-panel",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                children: "Generated Outputs"
            }, void 0, false, {
                fileName: "[project]/components/artifact-panel.tsx",
                lineNumber: 11,
                columnNumber: 44
            }, this),
            items.length === 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                children: "No generated outputs yet."
            }, void 0, false, {
                fileName: "[project]/components/artifact-panel.tsx",
                lineNumber: 11,
                columnNumber: 93
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                children: items.map((artifact)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                onClick: ()=>void preview(artifact),
                                children: artifact.name
                            }, void 0, false, {
                                fileName: "[project]/components/artifact-panel.tsx",
                                lineNumber: 11,
                                columnNumber: 186
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("a", {
                                href: __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["explorerApi"].downloadUrl(artifact.artifact_id),
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
            selected && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                        children: selected.name
                    }, void 0, false, {
                        fileName: "[project]/components/artifact-panel.tsx",
                        lineNumber: 11,
                        columnNumber: 359
                    }, this),
                    selected.media_type === "text/markdown" && content && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$markdown$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["SafeMarkdown"], {
                        content: content
                    }, void 0, false, {
                        fileName: "[project]/components/artifact-panel.tsx",
                        lineNumber: 11,
                        columnNumber: 438
                    }, this),
                    selected.media_type === "text/csv" && content && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("pre", {
                        children: content
                    }, void 0, false, {
                        fileName: "[project]/components/artifact-panel.tsx",
                        lineNumber: 11,
                        columnNumber: 523
                    }, this),
                    selected.media_type === "application/json" && content && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("pre", {
                        children: content
                    }, void 0, false, {
                        fileName: "[project]/components/artifact-panel.tsx",
                        lineNumber: 11,
                        columnNumber: 602
                    }, this),
                    selected.media_type.startsWith("image/") && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                        src: __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["explorerApi"].downloadUrl(selected.artifact_id),
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
_s(ArtifactPanel, "WPsxbNP2yXQXpCzNbYhi9TV7XB0=");
_c = ArtifactPanel;
var _c;
__turbopack_context__.k.register(_c, "ArtifactPanel");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/chart-renderer.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ChartRenderer",
    ()=>ChartRenderer,
    "prepareChart",
    ()=>prepareChart,
    "xAxisLabelPolicy",
    ()=>xAxisLabelPolicy
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$Area$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/cartesian/Area.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$chart$2f$AreaChart$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/chart/AreaChart.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$Bar$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/cartesian/Bar.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$chart$2f$BarChart$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/chart/BarChart.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$CartesianGrid$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/cartesian/CartesianGrid.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$Cell$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/component/Cell.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$Legend$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/component/Legend.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$Line$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/cartesian/Line.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$chart$2f$LineChart$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/chart/LineChart.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$polar$2f$Pie$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/polar/Pie.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$chart$2f$PieChart$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/chart/PieChart.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$ResponsiveContainer$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/component/ResponsiveContainer.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$Scatter$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/cartesian/Scatter.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$chart$2f$ScatterChart$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/chart/ScatterChart.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$Tooltip$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/component/Tooltip.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$XAxis$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/cartesian/XAxis.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$YAxis$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/recharts/es6/cartesian/YAxis.js [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
const COLORS = [
    "#176b87",
    "#3c9a79",
    "#d1873b",
    "#8064b5",
    "#cc5b63"
];
const SWITCHABLE_TYPES = [
    "line",
    "area",
    "bar"
];
const label = (spec, field, index)=>spec.series.find((series)=>series.field === field)?.label ?? field ?? `Series ${index + 1}`;
const supportsSwitching = (type)=>[
        "line",
        "area",
        "bar",
        "stacked_bar"
    ].includes(type);
function compactDate(value, includeYear = false) {
    const match = /^(\d{4})-(\d{2})(?:-\d{2})?$/.exec(String(value));
    if (!match) return String(value);
    const month = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec"
    ][Number(match[2]) - 1];
    return includeYear ? `${month} ’${match[1].slice(2)}` : month;
}
function truncateLabel(value, limit) {
    const text = String(value);
    return text.length <= limit ? text : `${text.slice(0, Math.max(limit - 1, 1)).trimEnd()}…`;
}
function xAxisLabelPolicy(data, xField, chartType) {
    const labels = data.map((row)=>String(row[xField] ?? ""));
    const isTime = labels.length > 0 && labels.every((value)=>/^\d{4}-\d{2}(-\d{2})?$/.test(value));
    const longest = Math.max(0, ...labels.map((value)=>value.length));
    // Preserve a maximum of eight time ticks. `interval={0}` renders every label
    // and is unreadable for long timelines or unpivoted comparison datasets.
    if (isTime) return {
        isTime: true,
        includeYear: new Set(labels.map((value)=>value.slice(0, 4))).size > 1,
        limit: 10,
        rotate: false,
        horizontalBars: false,
        interval: Math.max(0, Math.ceil(labels.length / 8) - 1)
    };
    // Category-label rule: short labels stay intact; medium labels are angled and
    // abbreviated; long or dense bar categories become horizontal bars. Full names
    // always remain available in the hover tooltip and source-data table.
    if (longest <= 12 && labels.length <= 8) return {
        isTime: false,
        includeYear: false,
        limit: 12,
        rotate: false,
        horizontalBars: false,
        interval: 0
    };
    if (longest <= 20 && labels.length <= 10) return {
        isTime: false,
        includeYear: false,
        limit: 16,
        rotate: true,
        horizontalBars: false,
        interval: Math.max(0, Math.ceil(labels.length / 8) - 1)
    };
    return {
        isTime: false,
        includeYear: false,
        limit: 18,
        rotate: true,
        horizontalBars: chartType === "bar" || chartType === "stacked_bar",
        interval: Math.max(0, Math.ceil(labels.length / 8) - 1)
    };
}
function prepareChart(chart) {
    const ordinarySeries = chart.y_fields.map((field, index)=>({
            field,
            label: label(chart, field, index),
            color: COLORS[index % COLORS.length]
        }));
    if (!chart.x_field || chart.y_fields.length !== 1 || ![
        "line",
        "area",
        "bar",
        "stacked_bar"
    ].includes(chart.type)) return {
        data: chart.data,
        series: ordinarySeries
    };
    const valueField = chart.y_fields[0];
    const columns = Object.keys(chart.data[0] ?? {}).filter((field)=>field !== chart.x_field && field !== valueField);
    const categoryField = columns.find((field)=>{
        const values = new Set(chart.data.map((row)=>row[field]).filter((value)=>typeof value === "string"));
        const xValues = new Set(chart.data.map((row)=>row[chart.x_field]));
        return values.size >= 2 && values.size <= 8 && chart.data.length > xValues.size;
    });
    if (!categoryField) return {
        data: chart.data,
        series: ordinarySeries
    };
    const categories = [
        ...new Set(chart.data.map((row)=>row[categoryField]).filter((value)=>typeof value === "string"))
    ];
    const fields = new Map(categories.map((category, index)=>[
            category,
            `${valueField}__series_${index}`
        ]));
    const rows = new Map();
    for (const row of chart.data){
        const xValue = row[chart.x_field];
        const category = row[categoryField];
        if (xValue === undefined || typeof category !== "string") continue;
        const key = String(xValue);
        const target = rows.get(key) ?? {
            [chart.x_field]: xValue
        };
        target[fields.get(category)] = row[valueField];
        rows.set(key, target);
    }
    return {
        data: [
            ...rows.values()
        ],
        series: categories.map((category, index)=>({
                field: fields.get(category),
                label: category,
                color: COLORS[index % COLORS.length]
            }))
    };
}
function formatValue(value, chart) {
    if (typeof value !== "number") return String(value);
    const rendered = new Intl.NumberFormat("en-US", {
        maximumFractionDigits: chart.formatting?.decimal_places ?? 0,
        notation: Math.abs(value) >= 1_000_000 ? "compact" : "standard"
    }).format(value);
    return chart.formatting?.currency ? `${chart.formatting.currency}${rendered}` : rendered;
}
function ChartRenderer({ chart }) {
    _s();
    const initialType = chart.type === "area" ? "area" : chart.type === "bar" || chart.type === "stacked_bar" ? "bar" : "line";
    const [visualType, setVisualType] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(initialType);
    const [showData, setShowData] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    if (chart.type === "kpi") return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "kpi-row",
        children: chart.kpis.map((kpi)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("article", {
                className: "kpi-card",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        children: kpi.label
                    }, void 0, false, {
                        fileName: "[project]/components/chart-renderer.tsx",
                        lineNumber: 71,
                        columnNumber: 132
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                        children: kpi.value
                    }, void 0, false, {
                        fileName: "[project]/components/chart-renderer.tsx",
                        lineNumber: 71,
                        columnNumber: 156
                    }, this),
                    kpi.change && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
                        children: kpi.change
                    }, void 0, false, {
                        fileName: "[project]/components/chart-renderer.tsx",
                        lineNumber: 71,
                        columnNumber: 199
                    }, this)
                ]
            }, kpi.label, true, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 71,
                columnNumber: 86
            }, this))
    }, void 0, false, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 71,
        columnNumber: 36
    }, this);
    if (!chart.data.length) return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "display-empty",
        children: "No chart data is available."
    }, void 0, false, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 72,
        columnNumber: 34
    }, this);
    if (chart.type === "table") return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(DataTable, {
        chart: chart
    }, void 0, false, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 73,
        columnNumber: 38
    }, this);
    if (!chart.x_field || !chart.y_fields.length) return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "display-empty",
        children: "This chart specification is incomplete."
    }, void 0, false, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 74,
        columnNumber: 56
    }, this);
    const renderType = supportsSwitching(chart.type) ? visualType : chart.type;
    const prepared = prepareChart(chart);
    const series = prepared.series;
    const labels = xAxisLabelPolicy(prepared.data, chart.x_field, renderType);
    const formatXAxis = (value)=>labels.isTime ? compactDate(value, labels.includeYear) : truncateLabel(value, labels.limit);
    const common = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$CartesianGrid$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["CartesianGrid"], {
                strokeDasharray: "3 3"
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 81,
                columnNumber: 20
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$XAxis$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["XAxis"], {
                dataKey: chart.x_field,
                tickFormatter: formatXAxis,
                interval: labels.interval,
                minTickGap: 8,
                angle: labels.rotate ? -30 : 0,
                textAnchor: labels.rotate ? "end" : "middle",
                height: labels.rotate ? 58 : 30
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 81,
                columnNumber: 59
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$YAxis$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["YAxis"], {
                width: 100,
                tickFormatter: (value)=>formatValue(value, chart)
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 81,
                columnNumber: 273
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$Tooltip$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Tooltip"], {
                formatter: (value)=>formatValue(value, chart),
                labelFormatter: (value)=>String(value)
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 81,
                columnNumber: 347
            }, this),
            chart.formatting?.show_legend !== false && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$Legend$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Legend"], {}, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 81,
                columnNumber: 493
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 81,
        columnNumber: 18
    }, this);
    const horizontalBarCommon = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$CartesianGrid$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["CartesianGrid"], {
                strokeDasharray: "3 3"
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 82,
                columnNumber: 33
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$XAxis$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["XAxis"], {
                type: "number",
                tickFormatter: (value)=>formatValue(value, chart)
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 82,
                columnNumber: 72
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$YAxis$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["YAxis"], {
                type: "category",
                dataKey: chart.x_field,
                width: 150,
                tickFormatter: (value)=>truncateLabel(value, 22)
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 82,
                columnNumber: 148
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$Tooltip$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Tooltip"], {
                formatter: (value)=>formatValue(value, chart),
                labelFormatter: (value)=>String(value)
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 82,
                columnNumber: 261
            }, this),
            chart.formatting?.show_legend !== false && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$Legend$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Legend"], {}, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 82,
                columnNumber: 407
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 82,
        columnNumber: 31
    }, this);
    let body;
    if (renderType === "line") body = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$chart$2f$LineChart$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["LineChart"], {
        data: prepared.data,
        margin: {
            top: 8,
            right: 18,
            bottom: 8,
            left: 8
        },
        children: [
            common,
            series.map((item)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$Line$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Line"], {
                    type: "monotone",
                    dataKey: item.field,
                    name: item.label,
                    stroke: item.color,
                    strokeWidth: 2,
                    dot: {
                        r: 3
                    },
                    activeDot: {
                        r: 5
                    }
                }, item.field, false, {
                    fileName: "[project]/components/chart-renderer.tsx",
                    lineNumber: 84,
                    columnNumber: 150
                }, this))
        ]
    }, void 0, true, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 84,
        columnNumber: 37
    }, this);
    else if (renderType === "area") body = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$chart$2f$AreaChart$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["AreaChart"], {
        data: prepared.data,
        margin: {
            top: 8,
            right: 18,
            bottom: 8,
            left: 8
        },
        children: [
            common,
            series.map((item)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$Area$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Area"], {
                    type: "monotone",
                    dataKey: item.field,
                    name: item.label,
                    stroke: item.color,
                    fill: item.color,
                    fillOpacity: .2
                }, item.field, false, {
                    fileName: "[project]/components/chart-renderer.tsx",
                    lineNumber: 85,
                    columnNumber: 155
                }, this))
        ]
    }, void 0, true, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 85,
        columnNumber: 42
    }, this);
    else if (renderType === "pie") body = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$chart$2f$PieChart$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["PieChart"], {
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$Tooltip$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Tooltip"], {
                formatter: (value)=>formatValue(value, chart)
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 86,
                columnNumber: 51
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$Legend$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Legend"], {}, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 86,
                columnNumber: 111
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$polar$2f$Pie$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Pie"], {
                data: chart.data,
                dataKey: chart.y_fields[0],
                nameKey: chart.x_field,
                outerRadius: 92,
                children: chart.data.map((_, index)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$Cell$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Cell"], {
                        fill: COLORS[index % COLORS.length]
                    }, index, false, {
                        fileName: "[project]/components/chart-renderer.tsx",
                        lineNumber: 86,
                        columnNumber: 243
                    }, this))
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 86,
                columnNumber: 121
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 86,
        columnNumber: 41
    }, this);
    else if (renderType === "scatter") body = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$chart$2f$ScatterChart$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ScatterChart"], {
        margin: {
            top: 8,
            right: 18,
            bottom: 8,
            left: 8
        },
        children: [
            common,
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$Scatter$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Scatter"], {
                data: chart.data,
                fill: COLORS[0]
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 87,
                columnNumber: 118
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 87,
        columnNumber: 45
    }, this);
    else if (labels.horizontalBars) body = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$chart$2f$BarChart$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["BarChart"], {
        data: prepared.data,
        layout: "vertical",
        margin: {
            top: 8,
            right: 18,
            bottom: 8,
            left: 8
        },
        children: [
            horizontalBarCommon,
            series.map((item)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$Bar$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Bar"], {
                    dataKey: item.field,
                    name: item.label,
                    fill: item.color,
                    stackId: chart.type === "stacked_bar" ? "stack" : undefined,
                    radius: [
                        0,
                        3,
                        3,
                        0
                    ]
                }, item.field, false, {
                    fileName: "[project]/components/chart-renderer.tsx",
                    lineNumber: 88,
                    columnNumber: 185
                }, this))
        ]
    }, void 0, true, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 88,
        columnNumber: 42
    }, this);
    else body = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$chart$2f$BarChart$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["BarChart"], {
        data: prepared.data,
        margin: {
            top: 8,
            right: 18,
            bottom: 8,
            left: 8
        },
        children: [
            common,
            series.map((item)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$cartesian$2f$Bar$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Bar"], {
                    dataKey: item.field,
                    name: item.label,
                    fill: item.color,
                    stackId: chart.type === "stacked_bar" ? "stack" : undefined,
                    radius: [
                        3,
                        3,
                        0,
                        0
                    ]
                }, item.field, false, {
                    fileName: "[project]/components/chart-renderer.tsx",
                    lineNumber: 89,
                    columnNumber: 127
                }, this))
        ]
    }, void 0, true, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 89,
        columnNumber: 15
    }, this);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
        className: "analytical-display",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                                children: chart.title
                            }, void 0, false, {
                                fileName: "[project]/components/chart-renderer.tsx",
                                lineNumber: 91,
                                columnNumber: 63
                            }, this),
                            chart.description && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                children: chart.description
                            }, void 0, false, {
                                fileName: "[project]/components/chart-renderer.tsx",
                                lineNumber: 91,
                                columnNumber: 107
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
                                children: [
                                    "Based on ",
                                    chart.source_query_ids.join(", ")
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/chart-renderer.tsx",
                                lineNumber: 91,
                                columnNumber: 134
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/chart-renderer.tsx",
                        lineNumber: 91,
                        columnNumber: 58
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "interactive-badge",
                        children: "Interactive"
                    }, void 0, false, {
                        fileName: "[project]/components/chart-renderer.tsx",
                        lineNumber: 91,
                        columnNumber: 199
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 91,
                columnNumber: 50
            }, this),
            supportsSwitching(chart.type) && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "chart-controls",
                "aria-label": "Chart display options",
                children: [
                    SWITCHABLE_TYPES.map((type)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                            type: "button",
                            className: visualType === type ? "active" : "",
                            "aria-pressed": visualType === type,
                            onClick: ()=>setVisualType(type),
                            children: type === "line" ? "Line" : type === "area" ? "Area" : "Bar"
                        }, type, false, {
                            fileName: "[project]/components/chart-renderer.tsx",
                            lineNumber: 91,
                            columnNumber: 395
                        }, this)),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        type: "button",
                        "aria-pressed": showData,
                        className: showData ? "active" : "",
                        onClick: ()=>setShowData((current)=>!current),
                        children: showData ? "Hide data" : "Show data"
                    }, void 0, false, {
                        fileName: "[project]/components/chart-renderer.tsx",
                        lineNumber: 91,
                        columnNumber: 619
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 91,
                columnNumber: 296
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "chart-canvas",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$recharts$2f$es6$2f$component$2f$ResponsiveContainer$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ResponsiveContainer"], {
                    width: "100%",
                    height: 310,
                    children: body
                }, void 0, false, {
                    fileName: "[project]/components/chart-renderer.tsx",
                    lineNumber: 91,
                    columnNumber: 837
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 91,
                columnNumber: 807
            }, this),
            showData && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(DataTable, {
                chart: chart,
                embedded: true
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 91,
                columnNumber: 931
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(CsvDownload, {
                chart: chart
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 91,
                columnNumber: 968
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 91,
        columnNumber: 10
    }, this);
}
_s(ChartRenderer, "9IJMomSdAygJZNMeB9lpESYJtgs=");
_c = ChartRenderer;
function DataTable({ chart, embedded = false }) {
    const columns = Object.keys(chart.data[0] ?? {});
    const content = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "data-table-wrap",
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("table", {
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("thead", {
                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("tr", {
                        children: columns.map((column)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("th", {
                                children: column
                            }, column, false, {
                                fileName: "[project]/components/chart-renderer.tsx",
                                lineNumber: 94,
                                columnNumber: 235
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/components/chart-renderer.tsx",
                        lineNumber: 94,
                        columnNumber: 206
                    }, this)
                }, void 0, false, {
                    fileName: "[project]/components/chart-renderer.tsx",
                    lineNumber: 94,
                    columnNumber: 199
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("tbody", {
                    children: chart.data.map((row, index)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("tr", {
                            children: columns.map((column)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("td", {
                                    children: formatValue(row[column], chart)
                                }, column, false, {
                                    fileName: "[project]/components/chart-renderer.tsx",
                                    lineNumber: 94,
                                    columnNumber: 360
                                }, this))
                        }, index, false, {
                            fileName: "[project]/components/chart-renderer.tsx",
                            lineNumber: 94,
                            columnNumber: 319
                        }, this))
                }, void 0, false, {
                    fileName: "[project]/components/chart-renderer.tsx",
                    lineNumber: 94,
                    columnNumber: 280
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/components/chart-renderer.tsx",
            lineNumber: 94,
            columnNumber: 192
        }, this)
    }, void 0, false, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 94,
        columnNumber: 159
    }, this);
    return embedded ? content : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
        className: "analytical-display",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                            children: chart.title
                        }, void 0, false, {
                            fileName: "[project]/components/chart-renderer.tsx",
                            lineNumber: 94,
                            columnNumber: 529
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
                            children: [
                                "Based on ",
                                chart.source_query_ids.join(", ")
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/chart-renderer.tsx",
                            lineNumber: 94,
                            columnNumber: 551
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/chart-renderer.tsx",
                    lineNumber: 94,
                    columnNumber: 524
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 94,
                columnNumber: 516
            }, this),
            content,
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(CsvDownload, {
                chart: chart
            }, void 0, false, {
                fileName: "[project]/components/chart-renderer.tsx",
                lineNumber: 94,
                columnNumber: 634
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 94,
        columnNumber: 476
    }, this);
}
_c1 = DataTable;
function CsvDownload({ chart }) {
    const download = ()=>{
        const fields = Object.keys(chart.data[0] ?? {});
        const csv = [
            fields.join(","),
            ...chart.data.map((row)=>fields.map((field)=>JSON.stringify(row[field] ?? "")).join(","))
        ].join("\n");
        const url = URL.createObjectURL(new Blob([
            csv
        ], {
            type: "text/csv"
        }));
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `${chart.id}.csv`;
        anchor.click();
        URL.revokeObjectURL(url);
    };
    return chart.data.length ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
        className: "csv-download",
        type: "button",
        onClick: download,
        children: "Download CSV"
    }, void 0, false, {
        fileName: "[project]/components/chart-renderer.tsx",
        lineNumber: 95,
        columnNumber: 513
    }, this) : null;
}
_c2 = CsvDownload;
var _c, _c1, _c2;
__turbopack_context__.k.register(_c, "ChartRenderer");
__turbopack_context__.k.register(_c1, "DataTable");
__turbopack_context__.k.register(_c2, "CsvDownload");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
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
"[project]/components/database-explorer.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "DatabaseExplorer",
    ()=>DatabaseExplorer
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/explorer.ts [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
function isDatabaseTable(value) {
    return Boolean(value && typeof value === "object" && typeof value.name === "string" && value.name.trim());
}
function DatabaseExplorer() {
    _s();
    const [tables, setTables] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const [selected, setSelected] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [loading, setLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [query, setQuery] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const panel = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "DatabaseExplorer.useEffect": ()=>{
            void __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["explorerApi"].tables().then({
                "DatabaseExplorer.useEffect": (result)=>setTables(Array.isArray(result?.tables) ? result.tables.filter(isDatabaseTable) : [])
            }["DatabaseExplorer.useEffect"]).catch({
                "DatabaseExplorer.useEffect": ()=>setError("Database schema is unavailable.")
            }["DatabaseExplorer.useEffect"]);
        }
    }["DatabaseExplorer.useEffect"], []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "DatabaseExplorer.useEffect": ()=>{
            if (selected) panel.current?.scrollIntoView?.({
                behavior: "smooth",
                block: "start"
            });
        }
    }["DatabaseExplorer.useEffect"], [
        selected
    ]);
    const choose = async (name)=>{
        if (selected?.name === name) {
            setSelected(null);
            return;
        }
        setLoading(name);
        try {
            setSelected(await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["explorerApi"].table(name));
            setError(null);
        } catch  {
            setError("Table details are unavailable.");
        } finally{
            setLoading(null);
        }
    };
    const shown = tables.filter((table)=>table.name.toLowerCase().includes(query.toLowerCase()));
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("aside", {
        className: "explorer-panel",
        ref: panel,
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                children: [
                    "Database ",
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
                        children: [
                            tables.length,
                            " tables"
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/database-explorer.tsx",
                        lineNumber: 23,
                        columnNumber: 18
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/database-explorer.tsx",
                lineNumber: 23,
                columnNumber: 5
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                "aria-label": "Search database schema",
                value: query,
                onChange: (event)=>setQuery(event.target.value),
                placeholder: "Search schema"
            }, void 0, false, {
                fileName: "[project]/components/database-explorer.tsx",
                lineNumber: 24,
                columnNumber: 5
            }, this),
            error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                children: error
            }, void 0, false, {
                fileName: "[project]/components/database-explorer.tsx",
                lineNumber: 25,
                columnNumber: 15
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "schema-layout",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("nav", {
                        children: shown.map((table)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                className: `schema-chip ${selected?.name === table.name ? "active" : ""} ${loading === table.name ? "loading" : ""}`,
                                "aria-pressed": selected?.name === table.name,
                                onClick: ()=>void choose(table.name),
                                children: table.name
                            }, table.name, false, {
                                fileName: "[project]/components/database-explorer.tsx",
                                lineNumber: 27,
                                columnNumber: 34
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/components/database-explorer.tsx",
                        lineNumber: 27,
                        columnNumber: 7
                    }, this),
                    selected && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                        className: "table-detail",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                                        children: selected.name
                                    }, void 0, false, {
                                        fileName: "[project]/components/database-explorer.tsx",
                                        lineNumber: 29,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                        className: "table-detail-close",
                                        "aria-label": "Close table details",
                                        onClick: ()=>setSelected(null),
                                        children: "×"
                                    }, void 0, false, {
                                        fileName: "[project]/components/database-explorer.tsx",
                                        lineNumber: 29,
                                        columnNumber: 41
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/database-explorer.tsx",
                                lineNumber: 29,
                                columnNumber: 9
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "table-detail-body",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h4", {
                                        children: [
                                            "Columns ",
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
                                                children: selected.columns.length
                                            }, void 0, false, {
                                                fileName: "[project]/components/database-explorer.tsx",
                                                lineNumber: 31,
                                                columnNumber: 23
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/components/database-explorer.tsx",
                                        lineNumber: 31,
                                        columnNumber: 11
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                                        children: selected.columns.map((column)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                                children: [
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                                        children: column.name
                                                    }, void 0, false, {
                                                        fileName: "[project]/components/database-explorer.tsx",
                                                        lineNumber: 32,
                                                        columnNumber: 71
                                                    }, this),
                                                    " ",
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        className: "column-type",
                                                        children: column.data_type
                                                    }, void 0, false, {
                                                        fileName: "[project]/components/database-explorer.tsx",
                                                        lineNumber: 32,
                                                        columnNumber: 102
                                                    }, this),
                                                    column.primary_key && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        className: "column-flag pk",
                                                        children: "PK"
                                                    }, void 0, false, {
                                                        fileName: "[project]/components/database-explorer.tsx",
                                                        lineNumber: 32,
                                                        columnNumber: 180
                                                    }, this),
                                                    !column.nullable && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        className: "column-flag",
                                                        children: "required"
                                                    }, void 0, false, {
                                                        fileName: "[project]/components/database-explorer.tsx",
                                                        lineNumber: 32,
                                                        columnNumber: 244
                                                    }, this)
                                                ]
                                            }, column.name, true, {
                                                fileName: "[project]/components/database-explorer.tsx",
                                                lineNumber: 32,
                                                columnNumber: 49
                                            }, this))
                                    }, void 0, false, {
                                        fileName: "[project]/components/database-explorer.tsx",
                                        lineNumber: 32,
                                        columnNumber: 11
                                    }, this),
                                    selected.foreign_keys.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h4", {
                                                children: "Relationships"
                                            }, void 0, false, {
                                                fileName: "[project]/components/database-explorer.tsx",
                                                lineNumber: 33,
                                                columnNumber: 50
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                                                className: "relationships",
                                                children: selected.foreign_keys.map((key, index)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                                        children: [
                                                            key.source_column,
                                                            " → ",
                                                            key.target_table,
                                                            ".",
                                                            key.target_column
                                                        ]
                                                    }, index, true, {
                                                        fileName: "[project]/components/database-explorer.tsx",
                                                        lineNumber: 33,
                                                        columnNumber: 145
                                                    }, this))
                                            }, void 0, false, {
                                                fileName: "[project]/components/database-explorer.tsx",
                                                lineNumber: 33,
                                                columnNumber: 72
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/components/database-explorer.tsx",
                                        lineNumber: 33,
                                        columnNumber: 48
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/database-explorer.tsx",
                                lineNumber: 30,
                                columnNumber: 9
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/database-explorer.tsx",
                        lineNumber: 28,
                        columnNumber: 20
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/database-explorer.tsx",
                lineNumber: 26,
                columnNumber: 5
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/database-explorer.tsx",
        lineNumber: 22,
        columnNumber: 10
    }, this);
}
_s(DatabaseExplorer, "c8Y0LGnCyO/vyfxgxS85/5uj7SQ=");
_c = DatabaseExplorer;
var _c;
__turbopack_context__.k.register(_c, "DatabaseExplorer");
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
"[project]/components/memory-inspector.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "MemoryInspector",
    ()=>MemoryInspector
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
const labels = {
    working: "Working",
    episodic: "Episodic",
    long_term: "Semantic / long-term"
};
function MemoryInspector() {
    _s();
    const [items, setItems] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const [type, setType] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "MemoryInspector.useEffect": ()=>{
            void (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/api/v1/memory${type ? `?memory_type=${type}` : ""}`).then(setItems).catch({
                "MemoryInspector.useEffect": ()=>setError("Memory inspection is unavailable.")
            }["MemoryInspector.useEffect"]);
        }
    }["MemoryInspector.useEffect"], [
        type
    ]);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("aside", {
        className: "memory-panel",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                children: "Memory"
            }, void 0, false, {
                fileName: "[project]/components/memory-inspector.tsx",
                lineNumber: 11,
                columnNumber: 42
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "muted",
                children: "Retained information for future reasoning—not chat history or run trace."
            }, void 0, false, {
                fileName: "[project]/components/memory-inspector.tsx",
                lineNumber: 11,
                columnNumber: 57
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("select", {
                "aria-label": "Memory type",
                value: type,
                onChange: (event)=>setType(event.target.value),
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                        value: "",
                        children: "All types"
                    }, void 0, false, {
                        fileName: "[project]/components/memory-inspector.tsx",
                        lineNumber: 11,
                        columnNumber: 265
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                        value: "long_term",
                        children: "Semantic / long-term"
                    }, void 0, false, {
                        fileName: "[project]/components/memory-inspector.tsx",
                        lineNumber: 11,
                        columnNumber: 300
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                        value: "episodic",
                        children: "Episodic"
                    }, void 0, false, {
                        fileName: "[project]/components/memory-inspector.tsx",
                        lineNumber: 11,
                        columnNumber: 355
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
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
            error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                children: error
            }, void 0, false, {
                fileName: "[project]/components/memory-inspector.tsx",
                lineNumber: 11,
                columnNumber: 456
            }, this),
            !error && items.length === 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "muted",
                children: "No retained memories."
            }, void 0, false, {
                fileName: "[project]/components/memory-inspector.tsx",
                lineNumber: 11,
                columnNumber: 504
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                children: items.map((memory)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                children: labels[memory.type]
                            }, void 0, false, {
                                fileName: "[project]/components/memory-inspector.tsx",
                                lineNumber: 11,
                                columnNumber: 598
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("time", {
                                children: new Date(memory.created_at).toLocaleString()
                            }, void 0, false, {
                                fileName: "[project]/components/memory-inspector.tsx",
                                lineNumber: 11,
                                columnNumber: 636
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                children: memory.content
                            }, void 0, false, {
                                fileName: "[project]/components/memory-inspector.tsx",
                                lineNumber: 11,
                                columnNumber: 695
                            }, this),
                            memory.run_id && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
                                children: [
                                    "Source run: ",
                                    memory.run_id
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/memory-inspector.tsx",
                                lineNumber: 11,
                                columnNumber: 736
                            }, this),
                            memory.session_id && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
                                children: [
                                    "Session: ",
                                    memory.session_id
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/memory-inspector.tsx",
                                lineNumber: 11,
                                columnNumber: 801
                            }, this),
                            typeof memory.metadata.category === "string" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("small", {
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
_s(MemoryInspector, "4up8POc8docd95nO5Srz+NJGEpo=");
_c = MemoryInspector;
var _c;
__turbopack_context__.k.register(_c, "MemoryInspector");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/run-chart-preview.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "RunChartPreview",
    ()=>RunChartPreview
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/explorer.ts [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
function RunChartPreview({ runId }) {
    _s();
    const [chart, setChart] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "RunChartPreview.useEffect": ()=>{
            let active = true;
            void __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["explorerApi"].artifacts(runId).then({
                "RunChartPreview.useEffect": (items)=>{
                    if (active) setChart(items.find({
                        "RunChartPreview.useEffect": (item)=>item.type === "chart" && item.media_type.startsWith("image/")
                    }["RunChartPreview.useEffect"]) ?? null);
                }
            }["RunChartPreview.useEffect"]).catch({
                "RunChartPreview.useEffect": ()=>{
                    if (active) setChart(null);
                }
            }["RunChartPreview.useEffect"]);
            return ({
                "RunChartPreview.useEffect": ()=>{
                    active = false;
                }
            })["RunChartPreview.useEffect"];
        }
    }["RunChartPreview.useEffect"], [
        runId
    ]);
    if (!chart) return null;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("figure", {
        className: "run-chart-preview",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                src: __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$explorer$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["explorerApi"].downloadUrl(chart.artifact_id),
                alt: chart.name
            }, void 0, false, {
                fileName: "[project]/components/run-chart-preview.tsx",
                lineNumber: 18,
                columnNumber: 48
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("figcaption", {
                children: [
                    "Generated chart: ",
                    chart.name
                ]
            }, void 0, true, {
                fileName: "[project]/components/run-chart-preview.tsx",
                lineNumber: 18,
                columnNumber: 173
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/run-chart-preview.tsx",
        lineNumber: 18,
        columnNumber: 10
    }, this);
}
_s(RunChartPreview, "emiLVeZDkQQszKK8qVrGGhsfzT4=");
_c = RunChartPreview;
var _c;
__turbopack_context__.k.register(_c, "RunChartPreview");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/features/workbench/run-analysis.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "RunAnalysis",
    ()=>RunAnalysis
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
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
    // Query-started, failed, and rejected events are execution noise. The Workbench
    // presents only completed queries because those are the queries used as evidence.
    if (event.type.startsWith("sql.") && event.type !== "sql.query_completed") return false;
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
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dl", {
        className: "run-metrics",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Duration"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 43
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: metric(metrics.total_duration_ms === null ? null : `${metrics.total_duration_ms}ms`)
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 60
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 50,
                columnNumber: 38
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Iterations"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 166
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: metrics.iterations
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 185
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 50,
                columnNumber: 161
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "SQL queries"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 225
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: metrics.database_query_count
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 245
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 50,
                columnNumber: 220
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Tool calls"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 295
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: metrics.tool_calls
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 314
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 50,
                columnNumber: 290
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Tokens"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 354
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        children: metric(metrics.total_tokens)
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 369
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 50,
                columnNumber: 349
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dt", {
                        children: "Estimated cost"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 419
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("dd", {
                        title: metrics.estimated_cost === null ? "Configure OpenAI per-million token prices on the backend to calculate this." : undefined,
                        children: metrics.estimated_cost === null ? "Not configured" : `$${metrics.estimated_cost.toFixed(4)}`
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 50,
                        columnNumber: 442
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 50,
                columnNumber: 414
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/features/workbench/run-analysis.tsx",
        lineNumber: 50,
        columnNumber: 10
    }, this);
}
_c = Metrics;
function RunAnalysis({ run, events, loading }) {
    _s();
    const [open, setOpen] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [filter, setFilter] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("all");
    const visible = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "RunAnalysis.useMemo[visible]": ()=>events.filter({
                "RunAnalysis.useMemo[visible]": (event)=>eventFilter(event, filter)
            }["RunAnalysis.useMemo[visible]"])
    }["RunAnalysis.useMemo[visible]"], [
        events,
        filter
    ]);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
        className: "run-analysis",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                className: "analysis-toggle",
                onClick: ()=>setOpen((value)=>!value),
                "aria-expanded": open,
                children: [
                    open ? "⌄" : "›",
                    " View analysis"
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 56,
                columnNumber: 44
            }, this),
            open && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "analysis-body",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "analysis-heading",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "eyebrow",
                                        children: "ANALYSIS RUN"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                        lineNumber: 56,
                                        columnNumber: 264
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                        children: run?.status === "failed" ? "Failed" : run?.status === "running" ? "Running" : "Completed"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                        lineNumber: 56,
                                        columnNumber: 309
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                lineNumber: 56,
                                columnNumber: 259
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Metrics, {
                                metrics: run?.metrics
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                lineNumber: 56,
                                columnNumber: 423
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 56,
                        columnNumber: 225
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "trace-filters",
                        children: FILTERS.map(([value, label])=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                className: filter === value ? "active" : "",
                                onClick: ()=>setFilter(value),
                                children: label
                            }, value, false, {
                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                lineNumber: 56,
                                columnNumber: 527
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 56,
                        columnNumber: 463
                    }, this),
                    loading && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "trace-empty",
                        children: "Loading structured trace…"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 56,
                        columnNumber: 661
                    }, this),
                    !loading && visible.length === 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "trace-empty",
                        children: "No public trace events are available for this run."
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 56,
                        columnNumber: 755
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ol", {
                        className: "trace-events",
                        children: visible.map((event)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                className: isFailure(event) ? "failure" : "",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "trace-icon",
                                        children: isFailure(event) ? "⚠" : event.type.endsWith("started") ? "●" : "✓"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                        lineNumber: 56,
                                        columnNumber: 955
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                                children: eventText(event)
                                            }, void 0, false, {
                                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                                lineNumber: 56,
                                                columnNumber: 1065
                                            }, this),
                                            event.type.startsWith("sql.") && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "query-details",
                                                children: [
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        children: [
                                                            "Status: ",
                                                            event.type === "sql.query_completed" ? "Completed" : event.type === "sql.query_failed" ? "Failed" : event.type === "sql.query_rejected" ? "Rejected" : "Running"
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                                        lineNumber: 56,
                                                        columnNumber: 1165
                                                    }, this),
                                                    typeof event.data.duration_ms === "number" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        children: [
                                                            "Duration: ",
                                                            event.data.duration_ms,
                                                            "ms"
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                                        lineNumber: 56,
                                                        columnNumber: 1395
                                                    }, this),
                                                    typeof event.data.row_count === "number" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        children: [
                                                            "Rows: ",
                                                            event.data.row_count
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                                        lineNumber: 56,
                                                        columnNumber: 1490
                                                    }, this),
                                                    Array.isArray(event.data.referenced_tables) && event.data.referenced_tables.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        children: [
                                                            "Tables: ",
                                                            event.data.referenced_tables.join(", ")
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                                        lineNumber: 56,
                                                        columnNumber: 1623
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("details", {
                                                        children: [
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("summary", {
                                                                children: "SQL"
                                                            }, void 0, false, {
                                                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                                                lineNumber: 56,
                                                                columnNumber: 1695
                                                            }, this),
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                                children: typeof event.data.sql === "string" ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("code", {
                                                                    children: event.data.sql
                                                                }, void 0, false, {
                                                                    fileName: "[project]/features/workbench/run-analysis.tsx",
                                                                    lineNumber: 56,
                                                                    columnNumber: 1758
                                                                }, this) : "SQL is not retained or exposed for this run."
                                                            }, void 0, false, {
                                                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                                                lineNumber: 56,
                                                                columnNumber: 1717
                                                            }, this)
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                                        lineNumber: 56,
                                                        columnNumber: 1686
                                                    }, this)
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                                lineNumber: 56,
                                                columnNumber: 1134
                                            }, this),
                                            typeof event.data.error === "string" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                className: "trace-reason",
                                                children: [
                                                    "Reason: ",
                                                    event.data.error
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                                lineNumber: 56,
                                                columnNumber: 1899
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/features/workbench/run-analysis.tsx",
                                        lineNumber: 56,
                                        columnNumber: 1060
                                    }, this)
                                ]
                            }, event.id, true, {
                                fileName: "[project]/features/workbench/run-analysis.tsx",
                                lineNumber: 56,
                                columnNumber: 890
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/run-analysis.tsx",
                        lineNumber: 56,
                        columnNumber: 837
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/run-analysis.tsx",
                lineNumber: 56,
                columnNumber: 194
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/features/workbench/run-analysis.tsx",
        lineNumber: 56,
        columnNumber: 10
    }, this);
}
_s(RunAnalysis, "L0SWxrZorai+l3wa3TK5hdfmLUo=");
_c1 = RunAnalysis;
var _c, _c1;
__turbopack_context__.k.register(_c, "Metrics");
__turbopack_context__.k.register(_c1, "RunAnalysis");
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
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$chat$2d$composer$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/chat-composer.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$markdown$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/markdown.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/analytics.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$conversations$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/conversations.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$features$2f$workbench$2f$run$2d$analysis$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/features/workbench/run-analysis.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$artifact$2d$panel$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/artifact-panel.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$database$2d$explorer$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/database-explorer.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$memory$2d$inspector$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/memory-inspector.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$features$2f$workbench$2f$status$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/features/workbench/status.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$approvals$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/approvals.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$approval$2d$card$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/approval-card.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$run$2d$chart$2d$preview$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/run-chart-preview.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$chart$2d$renderer$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/chart-renderer.tsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
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
;
;
;
const CONVERSATION_PAGE_SIZE = 8;
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
    _s();
    const [messages, setMessages] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const [status, setStatus] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [conversations, setConversations] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const [conversationId, setConversationId] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [historyError, setHistoryError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [conversationTotal, setConversationTotal] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(0);
    const [loadingMore, setLoadingMore] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [menuConversationId, setMenuConversationId] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [confirmDeleteId, setConfirmDeleteId] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [runs, setRuns] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])({});
    const [eventsByRun, setEventsByRun] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])({});
    const [loadingTraces, setLoadingTraces] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])({});
    const [approval, setApproval] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [approvalBusy, setApprovalBusy] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const source = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const terminalRun = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const finishing = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(false);
    const conversationGroups = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "Workbench.useMemo[conversationGroups]": ()=>groupConversations(conversations)
    }["Workbench.useMemo[conversationGroups]"], [
        conversations
    ]);
    const loadConversations = async (offset = 0, append = false)=>{
        try {
            const page = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$conversations$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["conversationsApi"].list(CONVERSATION_PAGE_SIZE, offset);
            setConversationTotal(page.total);
            setConversations((current)=>append ? [
                    ...current,
                    ...page.items.filter((item)=>!current.some((existing)=>existing.id === item.id))
                ] : page.items);
            setHistoryError(null);
        } catch  {
            setHistoryError("Conversation history could not be loaded.");
        }
    };
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Workbench.useEffect": ()=>{
            const timer = window.setTimeout({
                "Workbench.useEffect.timer": ()=>{
                    void loadConversations();
                }
            }["Workbench.useEffect.timer"], 0);
            return ({
                "Workbench.useEffect": ()=>window.clearTimeout(timer)
            })["Workbench.useEffect"];
        }
    }["Workbench.useEffect"], []);
    const switchConversation = async (id)=>{
        source.current?.close();
        terminalRun.current = null;
        finishing.current = false;
        setStatus(null);
        setError(null);
        try {
            const conversation = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$conversations$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["conversationsApi"].get(id);
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
                    await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["analyticsApi"].getEvents(run.run_id).then((result)=>result.items).catch(()=>[])
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
            run = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["analyticsApi"].getRun(runId);
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
                    metrics: run.metrics,
                    charts: run.charts ?? []
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
        else if (run.status === "waiting_for_approval") {
            const pending = (await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$approvals$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["approvalsApi"].list(runId)).find((item)=>item.status === "pending");
            setApproval(pending ?? null);
            setError(pending ? null : "The analyst is waiting for approval before making a protected change.");
        } else setError(run.error ?? "The analyst run ended without an answer.");
        setStatus(null);
        source.current?.close();
        source.current = null;
        void loadConversations();
    };
    const submit = async (message)=>{
        terminalRun.current = null;
        finishing.current = false;
        setApproval(null);
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
            const created = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["analyticsApi"].createRun({
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
                        metrics: null,
                        charts: []
                    }
                }));
            setEventsByRun((current)=>({
                    ...current,
                    [created.run_id]: []
                }));
            source.current = __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$analytics$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["analyticsApi"].connect(created.run_id, (event)=>{
                setEventsByRun((current)=>({
                        ...current,
                        [created.run_id]: current[created.run_id]?.some((existing)=>existing.id === event.id) ? current[created.run_id] : [
                            ...current[created.run_id] ?? [],
                            event
                        ]
                    }));
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
                    void loadConversations();
                }
            }, ()=>{
                if (terminalRun.current === created.run_id) return;
                setError("The progress stream disconnected. Checking the run status…");
                void finish(created.run_id).catch(()=>setStatus(null));
            });
        } catch (cause) {
            setStatus(null);
            setError(cause instanceof __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ApiError"] ? cause.message : "Unable to start the analyst run.");
        }
    };
    const newConversation = async ()=>{
        source.current?.close();
        terminalRun.current = null;
        finishing.current = false;
        setMessages([]);
        setRuns({});
        setEventsByRun({});
        setApproval(null);
        setStatus(null);
        setError(null);
        try {
            const conversation = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$conversations$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["conversationsApi"].create();
            setConversationId(conversation.id);
            setConversationTotal((total)=>total + 1);
            setConversations((current)=>[
                    conversation,
                    ...current.filter((item)=>item.id !== conversation.id)
                ].slice(0, CONVERSATION_PAGE_SIZE));
        } catch  {
            setHistoryError("A new conversation could not be created.");
        }
    };
    const showMoreConversations = async ()=>{
        setLoadingMore(true);
        try {
            await loadConversations(conversations.length, true);
        } finally{
            setLoadingMore(false);
        }
    };
    const renameConversation = async (conversation)=>{
        const title = window.prompt("Rename conversation", conversation.title)?.trim();
        if (!title || title === conversation.title) return;
        try {
            const updated = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$conversations$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["conversationsApi"].rename(conversation.id, title);
            setConversations((current)=>current.map((item)=>item.id === updated.id ? updated : item));
        } catch  {
            setHistoryError("Conversation could not be renamed.");
        } finally{
            setMenuConversationId(null);
        }
    };
    const deleteConversation = async (conversation)=>{
        if (confirmDeleteId !== conversation.id) {
            setConfirmDeleteId(conversation.id);
            return;
        }
        try {
            await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$conversations$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["conversationsApi"].remove(conversation.id);
            setConversations((current)=>current.filter((item)=>item.id !== conversation.id));
            setConversationTotal((total)=>Math.max(0, total - 1));
            setMenuConversationId(null);
            setConfirmDeleteId(null);
            if (conversationId === conversation.id) {
                source.current?.close();
                setConversationId(null);
                setMessages([]);
                setRuns({});
                setEventsByRun({});
                setStatus(null);
                setError(null);
            }
        } catch  {
            setHistoryError("Conversation could not be deleted.");
        }
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
                                lineNumber: 132,
                                columnNumber: 12
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                                children: "AI Data Analyst"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 132,
                                columnNumber: 54
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 132,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        className: "new-conversation",
                        onClick: ()=>void newConversation(),
                        children: "＋ New conversation"
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 133,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                children: "CONVERSATIONS"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 134,
                                columnNumber: 16
                            }, this),
                            historyError && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "muted",
                                role: "alert",
                                children: historyError
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 134,
                                columnNumber: 53
                            }, this),
                            !historyError && conversations.length === 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "muted",
                                children: "No saved conversations yet."
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 134,
                                columnNumber: 160
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("nav", {
                                className: "conversation-groups",
                                "aria-label": "Conversations",
                                children: conversationGroups.map((group)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "conversation-group",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                                                children: group.label
                                            }, void 0, false, {
                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                lineNumber: 135,
                                                columnNumber: 162
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "conversation-list",
                                                children: group.items.map((conversation)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                        className: `conversation-item ${conversation.id === conversationId ? "active" : ""}`,
                                                        children: [
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                                className: "conversation-select",
                                                                onClick: ()=>void switchConversation(conversation.id),
                                                                title: conversation.title,
                                                                children: conversation.title
                                                            }, void 0, false, {
                                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                                lineNumber: 135,
                                                                columnNumber: 367
                                                            }, this),
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                                className: "conversation-menu-wrap",
                                                                children: [
                                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                                        className: "conversation-menu-toggle",
                                                                        "aria-label": `Conversation options for ${conversation.title}`,
                                                                        "aria-expanded": menuConversationId === conversation.id,
                                                                        onClick: ()=>{
                                                                            setConfirmDeleteId(null);
                                                                            setMenuConversationId((current)=>current === conversation.id ? null : conversation.id);
                                                                        },
                                                                        children: "•••"
                                                                    }, void 0, false, {
                                                                        fileName: "[project]/features/workbench/workbench.tsx",
                                                                        lineNumber: 135,
                                                                        columnNumber: 560
                                                                    }, this),
                                                                    menuConversationId === conversation.id && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                                        className: "conversation-menu",
                                                                        role: "menu",
                                                                        children: [
                                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                                                role: "menuitem",
                                                                                onClick: ()=>void renameConversation(conversation),
                                                                                children: "Rename"
                                                                            }, void 0, false, {
                                                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                                                lineNumber: 135,
                                                                                columnNumber: 960
                                                                            }, this),
                                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                                                role: "menuitem",
                                                                                className: "delete-conversation",
                                                                                onClick: ()=>void deleteConversation(conversation),
                                                                                children: confirmDeleteId === conversation.id ? "Confirm delete" : "Delete"
                                                                            }, void 0, false, {
                                                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                                                lineNumber: 135,
                                                                                columnNumber: 1053
                                                                            }, this),
                                                                            confirmDeleteId === conversation.id && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                                                role: "menuitem",
                                                                                onClick: ()=>setConfirmDeleteId(null),
                                                                                children: "Cancel"
                                                                            }, void 0, false, {
                                                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                                                lineNumber: 135,
                                                                                columnNumber: 1279
                                                                            }, this)
                                                                        ]
                                                                    }, void 0, true, {
                                                                        fileName: "[project]/features/workbench/workbench.tsx",
                                                                        lineNumber: 135,
                                                                        columnNumber: 913
                                                                    }, this)
                                                                ]
                                                            }, void 0, true, {
                                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                                lineNumber: 135,
                                                                columnNumber: 520
                                                            }, this)
                                                        ]
                                                    }, conversation.id, true, {
                                                        fileName: "[project]/features/workbench/workbench.tsx",
                                                        lineNumber: 135,
                                                        columnNumber: 254
                                                    }, this))
                                            }, void 0, false, {
                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                lineNumber: 135,
                                                columnNumber: 184
                                            }, this)
                                        ]
                                    }, group.label, true, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 135,
                                        columnNumber: 108
                                    }, this))
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 135,
                                columnNumber: 9
                            }, this),
                            !historyError && conversations.length < conversationTotal && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                className: "show-more-conversations",
                                onClick: ()=>void showMoreConversations(),
                                disabled: loadingMore,
                                children: loadingMore ? "Loading…" : `Show more (${conversationTotal - conversations.length})`
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 136,
                                columnNumber: 71
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 134,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$artifact$2d$panel$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ArtifactPanel"], {
                        runIds: Object.keys(runs),
                        refreshKey: Object.values(runs).map((run)=>`${run.run_id}:${run.status}:${run.completed_at ?? ""}`).join(",")
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 138,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$database$2d$explorer$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["DatabaseExplorer"], {}, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 139,
                        columnNumber: 7
                    }, this),
                    __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].env.NEXT_PUBLIC_DEVELOPER_MODE === "true" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$memory$2d$inspector$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["MemoryInspector"], {}, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 140,
                        columnNumber: 61
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/workbench.tsx",
                lineNumber: 131,
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
                                        lineNumber: 142,
                                        columnNumber: 52
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                                        children: "AI Data Analyst"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 142,
                                        columnNumber: 101
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 142,
                                columnNumber: 47
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "connection",
                                children: "● Backend connected"
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 142,
                                columnNumber: 131
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 142,
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
                                        lineNumber: 143,
                                        columnNumber: 112
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                        children: "Try investigating revenue changes, customer behavior, conversion, or operational performance."
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 143,
                                        columnNumber: 151
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 143,
                                columnNumber: 89
                            }, this),
                            messages.map((message, index)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "message-with-analysis",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("article", {
                                            className: `message ${message.role}`,
                                            "data-run-id": message.run_id ?? undefined,
                                            children: message.role === "assistant" ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$markdown$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["SafeMarkdown"], {
                                                content: message.content
                                            }, void 0, false, {
                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                lineNumber: 143,
                                                columnNumber: 500
                                            }, this) : message.content
                                        }, void 0, false, {
                                            fileName: "[project]/features/workbench/workbench.tsx",
                                            lineNumber: 143,
                                            columnNumber: 379
                                        }, this),
                                        message.role === "assistant" && message.run_id && runs[message.run_id]?.charts?.map((chart)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$chart$2d$renderer$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ChartRenderer"], {
                                                chart: chart
                                            }, chart.id, false, {
                                                fileName: "[project]/features/workbench/workbench.tsx",
                                                lineNumber: 143,
                                                columnNumber: 667
                                            }, this)),
                                        message.role === "assistant" && message.run_id && !runs[message.run_id]?.charts?.length && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$run$2d$chart$2d$preview$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["RunChartPreview"], {
                                            runId: message.run_id
                                        }, void 0, false, {
                                            fileName: "[project]/features/workbench/workbench.tsx",
                                            lineNumber: 143,
                                            columnNumber: 809
                                        }, this),
                                        message.role === "assistant" && message.run_id && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$features$2f$workbench$2f$run$2d$analysis$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["RunAnalysis"], {
                                            run: runs[message.run_id],
                                            events: eventsByRun[message.run_id] ?? [],
                                            loading: loadingTraces[message.run_id]
                                        }, void 0, false, {
                                            fileName: "[project]/features/workbench/workbench.tsx",
                                            lineNumber: 143,
                                            columnNumber: 903
                                        }, this)
                                    ]
                                }, `${message.run_id ?? "message"}-${index}`, true, {
                                    fileName: "[project]/features/workbench/workbench.tsx",
                                    lineNumber: 143,
                                    columnNumber: 292
                                }, this)),
                            status && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "progress",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "spinner"
                                    }, void 0, false, {
                                        fileName: "[project]/features/workbench/workbench.tsx",
                                        lineNumber: 143,
                                        columnNumber: 1074
                                    }, this),
                                    status
                                ]
                            }, void 0, true, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 143,
                                columnNumber: 1048
                            }, this),
                            approval && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$approval$2d$card$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ApprovalCard"], {
                                approval: approval,
                                busy: approvalBusy,
                                onApprove: ()=>{
                                    setApprovalBusy(true);
                                    void __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$approvals$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["approvalsApi"].approve(approval.id).then(()=>{
                                        finishing.current = false;
                                        setApproval(null);
                                        return finish(approval.run_id);
                                    }).catch(()=>setError("Approval could not be completed.")).finally(()=>setApprovalBusy(false));
                                },
                                onReject: ()=>{
                                    setApprovalBusy(true);
                                    void __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$approvals$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["approvalsApi"].reject(approval.id).then(()=>{
                                        finishing.current = false;
                                        setApproval(null);
                                        return finish(approval.run_id);
                                    }).catch(()=>setError("Approval could not be completed.")).finally(()=>setApprovalBusy(false));
                                }
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 143,
                                columnNumber: 1130
                            }, this),
                            error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "error",
                                role: "alert",
                                children: error
                            }, void 0, false, {
                                fileName: "[project]/features/workbench/workbench.tsx",
                                lineNumber: 143,
                                columnNumber: 1745
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 143,
                        columnNumber: 7
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$chat$2d$composer$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ChatComposer"], {
                        onSubmit: submit,
                        disabled: Boolean(status)
                    }, void 0, false, {
                        fileName: "[project]/features/workbench/workbench.tsx",
                        lineNumber: 144,
                        columnNumber: 7
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/features/workbench/workbench.tsx",
                lineNumber: 142,
                columnNumber: 5
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/features/workbench/workbench.tsx",
        lineNumber: 130,
        columnNumber: 10
    }, this);
}
_s(Workbench, "blA2Q5iawl3PauSqFDm85D6eKqw=");
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
    getEvents: (runId)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/api/v1/analytics/runs/${runId}/events/history`),
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
"[project]/lib/api/approvals.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "approvalsApi",
    ()=>approvalsApi
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-client] (ecmascript)");
;
const approvalsApi = {
    list: (runId)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/runs/${runId}/approvals`),
    approve: (id)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/approvals/${id}/approve`, {
            method: "POST"
        }),
    reject: (id)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/approvals/${id}/reject`, {
            method: "POST"
        })
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
"[project]/lib/api/conversations.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "conversationsApi",
    ()=>conversationsApi
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-client] (ecmascript)");
;
const conversationsApi = {
    create: (title = "New conversation")=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])("/api/v1/conversations", {
            method: "POST",
            body: JSON.stringify({
                title
            })
        }),
    list: (limit = 30, offset = 0)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/api/v1/conversations?limit=${limit}&offset=${offset}`),
    get: (id, messageLimit = 100, messageOffset = 0)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/api/v1/conversations/${id}?message_limit=${messageLimit}&message_offset=${messageOffset}`),
    rename: (id, title)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/api/v1/conversations/${id}`, {
            method: "PATCH",
            body: JSON.stringify({
                title
            })
        }),
    remove: (id)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/api/v1/conversations/${id}`, {
            method: "DELETE"
        })
};
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/lib/api/explorer.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "explorerApi",
    ()=>explorerApi
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api/client.ts [app-client] (ecmascript)");
;
const explorerApi = {
    artifacts: (runId)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/artifacts${runId ? `?run_id=${encodeURIComponent(runId)}` : ""}`),
    preview: (id)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/artifacts/${id}/preview`),
    downloadUrl: (id)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["eventUrl"])(`/artifacts/${id}`),
    tables: ()=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])("/api/v1/schema/tables"),
    search: (query)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/api/v1/schema/search?q=${encodeURIComponent(query)}`),
    table: (name)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2f$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["request"])(`/api/v1/schema/tables/${encodeURIComponent(name)}`)
};
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=_0-2kx1_._.js.map