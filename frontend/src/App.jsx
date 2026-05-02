import { useEffect, useRef, useState } from "react";
import { Cat, Dog, ExternalLink, Heart, PawPrint, Send, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Custom components for the markdown coming from the bot.
// Profile links are styled as pill buttons; images are larger thumbnails.
const MARKDOWN_COMPONENTS = {
  a: ({ href, children, ...props }) => {
    const isProfile =
      typeof href === "string" && /\/animal\/|\/dogs?\/|\/cats?-?1?\//.test(href);

    if (isProfile) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="not-prose mt-2 inline-flex items-center gap-1.5 rounded-full bg-gradient-to-br from-pink-400 to-rose-400 px-4 py-1.5 text-xs font-semibold text-white shadow-md shadow-pink-200/60 transition hover:-translate-y-0.5 hover:shadow-lg"
        >
          View profile
          <ExternalLink size={13} />
        </a>
      );
    }

    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium text-pink-600 underline-offset-2 hover:text-pink-700"
        {...props}
      >
        {children}
      </a>
    );
  },
  img: (props) => (
    <img
      {...props}
      className="not-prose my-2 h-44 w-44 rounded-2xl object-cover shadow-md ring-1 ring-orange-100"
      loading="lazy"
    />
  ),
};

const STARTER_MESSAGES = [
  "I want a young friendly female dog",
  "אני רוצה כלבה צעירה וחברותית",
  "Find me a calm black cat",
  "Do you have a kitten that is good with dogs?",
];

function ChatBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={[
        "mb-5 flex gap-3",
        isUser ? "justify-end" : "justify-start",
      ].join(" ")}
    >
      {!isUser && (
        <div className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-orange-100 text-orange-800 shadow-sm">
          <PawPrint size={18} />
        </div>
      )}

      <div
        className={[
          "max-w-[76%] break-words rounded-[22px] px-4 py-3 leading-relaxed shadow-lg",
          isUser
            ? "whitespace-pre-wrap rounded-br-lg bg-gradient-to-br from-pink-400 to-rose-400 text-white"
            : "rounded-bl-lg border border-orange-100 bg-white text-slate-700",
        ].join(" ")}
      >
        <div
          className={[
            "mb-1 text-xs font-bold tracking-wide opacity-70",
            isUser ? "text-white" : "text-slate-600",
          ].join(" ")}
        >
          {isUser ? "You" : "Adoption Assistant"}
        </div>

        {isUser ? (
          <div className="text-[0.98rem]">{message.content}</div>
        ) : (
          <div className="prose prose-sm prose-slate max-w-none prose-headings:mb-1 prose-headings:mt-3 prose-headings:text-base prose-headings:font-bold prose-p:my-1.5 prose-strong:text-slate-900 prose-ol:my-2 prose-ol:space-y-3 prose-ul:my-1 prose-ul:space-y-0.5 prose-li:my-0 prose-li:leading-relaxed marker:text-pink-400">
            <ReactMarkdown components={MARKDOWN_COMPONENTS}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {isUser && (
        <div className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-pink-100 text-pink-700 shadow-sm">
          <Heart size={18} />
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="mb-5 flex justify-start gap-3">
      <div className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-orange-100 text-orange-800 shadow-sm">
        <PawPrint size={18} />
      </div>

      <div className="flex h-11 w-[76px] items-center gap-1.5 rounded-[22px] rounded-bl-lg border border-orange-100 bg-white px-4 shadow-lg">
        <span className="h-2 w-2 animate-blink rounded-full bg-orange-300" />
        <span className="h-2 w-2 animate-blink rounded-full bg-orange-300 [animation-delay:150ms]" />
        <span className="h-2 w-2 animate-blink rounded-full bg-orange-300 [animation-delay:300ms]" />
      </div>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! I’m your adoption assistant 🐾 Tell me what kind of dog or cat you’re hoping to find — age, color, breed, gender, or personality.",
    },
  ]);

  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function sendMessage(textFromButton = null) {
    const text = (textFromButton || input).trim();

    if (!text || isLoading) {
      return;
    }

    setInput("");
    setErrorMessage("");

    setMessages((current) => [
      ...current,
      {
        role: "user",
        content: text,
      },
    ]);

    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: text,
          ...(threadId ? { thread_id: threadId } : {}),
        }),
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        throw new Error(errorBody?.detail || "Failed to get response");
      }

      const data = await response.json();

      setThreadId(data.thread_id);

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: data.answer,
        },
      ]);
    } catch (error) {
      const message = error.message || "Something went wrong";

      setErrorMessage(message);

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            "Oops, I had trouble reaching the adoption assistant. Please check that the API is running and try again 🐶",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendMessage();
  }

  function startNewChat() {
    setThreadId(null);
    setInput("");
    setErrorMessage("");
    setMessages([
      {
        role: "assistant",
        content:
          "New search started 🐾 What kind of companion are you hoping to find?",
      },
    ]);
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-orange-50 via-pink-50 to-emerald-50 p-7 text-slate-800">
      <div className="absolute left-[8%] top-[8%] h-44 w-44 animate-float rounded-full bg-orange-200/60 blur-sm" />
      <div className="absolute bottom-[8%] right-[9%] h-56 w-56 animate-float rounded-full bg-emerald-200/60 blur-sm [animation-delay:1.4s]" />
      <div className="absolute right-[18%] top-[18%] h-36 w-36 animate-float rounded-full bg-sky-200/60 blur-sm [animation-delay:2.2s]" />

      <main className="relative z-10 flex h-[min(860px,calc(100vh-56px))] w-full max-w-5xl flex-col overflow-hidden rounded-[34px] border border-orange-200/60 bg-white/80 shadow-2xl shadow-orange-950/10 backdrop-blur-xl max-md:h-screen max-md:rounded-none">
        <header className="flex items-center justify-between gap-5 border-b border-orange-100 bg-orange-50/70 p-6 max-md:items-start max-md:p-4">
          <div className="flex items-center gap-4">
            <div className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-orange-200 to-pink-300 text-orange-900 shadow-lg shadow-pink-200/60 max-md:h-12 max-md:w-12">
              <PawPrint size={28} />
            </div>

            <div>
              <h1 className="m-0 text-3xl font-extrabold tracking-tight text-slate-800 max-md:text-xl">
                Adoption Assistant
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                Find your next furry best friend
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={startNewChat}
            className="inline-flex items-center gap-2 rounded-full bg-orange-100 px-4 py-2.5 text-sm font-semibold text-orange-900 shadow-inner transition hover:-translate-y-0.5 hover:bg-orange-200 hover:shadow-md"
          >
            <Sparkles size={16} />
            New search
          </button>
        </header>

        <section className="mx-6 mt-5 flex items-center gap-4 rounded-3xl bg-gradient-to-br from-emerald-100/80 to-sky-100/80 p-4 max-md:mx-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center gap-1 rounded-2xl bg-white/80 text-slate-700">
            <Dog size={22} />
            <Cat size={22} />
          </div>

          <div>
            <strong className="block text-slate-700">Ask naturally.</strong>
            <span className="text-sm text-slate-500">
              Try “young friendly dog”, “חתול שחור רגוע”, or “female puppy”.
            </span>
          </div>
        </section>

        <section className="flex gap-2 overflow-x-auto px-6 pb-1 pt-4 max-md:px-4">
          {STARTER_MESSAGES.map((starter) => (
            <button
              key={starter}
              type="button"
              onClick={() => sendMessage(starter)}
              disabled={isLoading}
              className="shrink-0 rounded-full border border-orange-100 bg-white/90 px-3.5 py-2 text-sm text-slate-600 shadow-sm transition hover:-translate-y-0.5 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {starter}
            </button>
          ))}
        </section>

        <section className="flex-1 overflow-y-auto px-6 py-5 max-md:px-4">
          {messages.map((message, index) => (
            <ChatBubble key={`${message.role}-${index}`} message={message} />
          ))}

          {isLoading && <TypingIndicator />}

          <div ref={messagesEndRef} />
        </section>

        {errorMessage && (
          <div className="mx-6 mb-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 max-md:mx-4">
            {errorMessage}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="flex gap-3 border-t border-orange-100 bg-orange-50/70 px-6 py-5 max-md:px-4"
        >
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Describe your dream dog or cat..."
            maxLength={1000}
            className="min-w-0 flex-1 rounded-full border border-orange-100 bg-white px-5 py-4 text-slate-700 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-pink-300 focus:ring-4 focus:ring-pink-100"
          />

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-pink-400 to-rose-400 text-white shadow-lg shadow-pink-300/40 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send size={19} />
          </button>
        </form>
      </main>
    </div>
  );
}