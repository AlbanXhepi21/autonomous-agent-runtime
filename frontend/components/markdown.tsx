import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function SqlCode({ children }: { children: string }) {
  const pieces = children.split(/(\b(?:SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|GROUP|ORDER|BY|AS|ON|AND|OR|COUNT|SUM|AVG|LIMIT|WITH)\b)/gi);
  return <code className="sql-code">{pieces.map((piece, index) => /^(select|from|where|join|left|right|inner|group|order|by|as|on|and|or|count|sum|avg|limit|with)$/i.test(piece) ? <span className="sql-keyword" key={index}>{piece}</span> : piece)}</code>;
}

export function SafeMarkdown({ content }: { content: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
    code({ className, children }) {
      const value = String(children).replace(/\n$/, "");
      return className?.includes("language-sql") ? <SqlCode>{value}</SqlCode> : <code className={className}>{children}</code>;
    }
  }}>{content}</ReactMarkdown>;
}
