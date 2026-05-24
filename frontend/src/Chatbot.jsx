import { useEffect, useRef, useState } from "react";
import { askQuestion } from "./services/queryService";

const initialMessages = [
  {
    id: crypto.randomUUID(),
    role: "assistant",
    text: "Hi! Ask me anything about your supply chain data.",
  },
];

export default function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [isWaiting, setIsWaiting] = useState(false);
  const wrapperRef = useRef(null);
  const bottomRef = useRef(null);

  function openChatbot() {
    setIsVisible(true);
    requestAnimationFrame(() => setIsOpen(true));
  }

  function closeChatbot() {
    setIsOpen(false);
    setTimeout(() => setIsVisible(false), 220);
  }

  useEffect(() => {
    function handleClickOutside(event) {
      if (
        isOpen &&
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target)
      ) {
        closeChatbot();
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isWaiting]);

  async function handleSubmit(event) {
    event.preventDefault();

    const question = input.trim();
    if (!question || isWaiting) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: question,
    };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setIsWaiting(true);

    try {
      const data = await askQuestion(question);

      const answer =
        data.answer ??
        (data.count === 0
          ? "I did not find matching records for this question."
          : formatAnswer(data));

      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: answer,
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text:
            error.message ??
            "Sorry, I could not reach the query service. Please try again.",
          isError: true,
        },
      ]);
    } finally {
      setIsWaiting(false);
    }
  }

  return (
    <div ref={wrapperRef} style={styles.wrapper}>
      {isVisible ? (
        <section
          style={{
            ...styles.chatWindow,
            ...(isOpen ? styles.chatWindowOpen : styles.chatWindowClosed),
          }}
        >
          <header style={styles.header}>
            <div>
              <h3 style={styles.title}>Supply Chain Assistant</h3>
              <p style={styles.subtitle}>
                Ask questions about orders, delays, risks, and markets
              </p>
            </div>
            <button onClick={closeChatbot} style={styles.closeButton}>
              ×
            </button>
          </header>

          <div style={styles.messagesPanel}>
            {messages.map((message) => (
              <div
                key={message.id}
                style={{
                  ...styles.messageRow,
                  justifyContent:
                    message.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    ...styles.messageBubble,
                    ...(message.role === "user"
                      ? styles.userBubble
                      : message.isError
                        ? styles.errorBubble
                        : styles.botBubble),
                  }}
                >
                  {message.text}
                </div>
              </div>
            ))}

            {isWaiting && (
              <div style={styles.messageRow}>
                <div style={{ ...styles.messageBubble, ...styles.botBubble }}>
                  <span style={styles.typingDot}>●</span>
                  <span style={styles.typingDot}>●</span>
                  <span style={styles.typingDot}>●</span>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSubmit} style={styles.form}>
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about late deliveries..."
              style={styles.input}
              disabled={isWaiting}
            />
            <button
              type="submit"
              disabled={!input.trim() || isWaiting}
              style={{
                ...styles.sendButton,
                opacity: !input.trim() || isWaiting ? 0.55 : 1,
                cursor: !input.trim() || isWaiting ? "not-allowed" : "pointer",
              }}
            >
              Send
            </button>
          </form>
        </section>
      ) : (
        <button onClick={openChatbot} style={styles.floatingButton}>
          💬
        </button>
      )}
    </div>
  );
}

function formatAnswer(data) {
  const rows = data.data ?? [];
  const preview = rows.slice(0, 5);

  return [
    `Found ${data.count} result${data.count === 1 ? "" : "s"}.`,
    ...preview.map((row, index) => `${index + 1}. ${formatRow(row)}`),
    data.count > preview.length
      ? `Showing first ${preview.length} results.`
      : "",
  ]
    .filter(Boolean)
    .join("\n");
}

function formatRow(row) {
  return Object.entries(row)
    .map(([key, value]) => `${key}: ${formatValue(value)}`)
    .join(" · ");
}

function formatValue(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number")
    return Number.isInteger(value) ? value : value.toFixed(2);
  return String(value);
}

const styles = {
  wrapper: {
    position: "fixed",
    right: "24px",
    bottom: "24px",
    zIndex: 20,
  },
  floatingButton: {
    width: "58px",
    height: "58px",
    borderRadius: "18px",
    border: "1px solid #8b5cf655",
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    color: "#fff",
    fontSize: "24px",
    boxShadow: "0 12px 35px rgba(99,102,241,0.4)",
    cursor: "pointer",
  },
  chatWindow: {
    width: "380px",
    height: "520px",
    background: "#0f172a",
    border: "1px solid #1e293b",
    borderRadius: "18px",
    boxShadow: "0 18px 60px rgba(0,0,0,0.45)",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    transformOrigin: "bottom right",
    transition: "opacity 220ms ease, transform 220ms ease",
  },
  chatWindowOpen: {
    opacity: 1,
    transform: "scale(1) translateY(0)",
  },
  chatWindowClosed: {
    opacity: 0,
    transform: "scale(0.82) translateY(24px)",
    pointerEvents: "none",
  },
  header: {
    padding: "18px",
    borderBottom: "1px solid #1e293b",
    display: "flex",
    justifyContent: "space-between",
    gap: "12px",
    background:
      "linear-gradient(135deg, rgba(99,102,241,0.18), rgba(15,23,42,0.95))",
  },
  title: {
    margin: 0,
    color: "#f1f5f9",
    fontSize: "16px",
    fontWeight: 700,
  },
  subtitle: {
    margin: "4px 0 0",
    color: "#64748b",
    fontSize: "12px",
    lineHeight: 1.35,
  },
  closeButton: {
    width: "30px",
    height: "30px",
    borderRadius: "10px",
    border: "1px solid #334155",
    background: "#0a0f1e",
    color: "#94a3b8",
    fontSize: "20px",
    cursor: "pointer",
  },
  messagesPanel: {
    flex: 1,
    padding: "16px",
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    background: "#0a0f1e",
  },
  messageRow: {
    display: "flex",
  },
  messageBubble: {
    maxWidth: "82%",
    padding: "10px 12px",
    borderRadius: "14px",
    fontSize: "13px",
    lineHeight: 1.45,
    whiteSpace: "pre-wrap",
  },
  userBubble: {
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    color: "#fff",
    borderBottomRightRadius: "4px",
  },
  botBubble: {
    background: "#111c31",
    color: "#cbd5e1",
    border: "1px solid #1e293b",
    borderBottomLeftRadius: "4px",
  },
  errorBubble: {
    background: "#ff1e1e18",
    color: "#ff6b6b",
    border: "1px solid #ff4d4d44",
  },
  typingDot: {
    color: "#818cf8",
    marginRight: "4px",
    fontSize: "10px",
  },
  form: {
    display: "flex",
    gap: "10px",
    padding: "14px",
    borderTop: "1px solid #1e293b",
    background: "#0f172a",
  },
  input: {
    flex: 1,
    border: "1px solid #1e293b",
    borderRadius: "12px",
    background: "#080c14",
    color: "#e2e8f0",
    padding: "12px",
    outline: "none",
    fontSize: "13px",
  },
  sendButton: {
    border: "none",
    borderRadius: "12px",
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    color: "#fff",
    padding: "0 16px",
    fontWeight: 700,
  },
};
