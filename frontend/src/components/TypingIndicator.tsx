import React, { useEffect, useState } from "react";

const TypingIndicator: React.FC = () => {
  const [dots, setDots] = useState(1);

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev >= 3 ? 1 : prev + 1));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        padding: "10px 14px",
        color: "#9ca3af",
        fontSize: "14px",
        fontStyle: "italic",
      }}
    >
      <span
        style={{
          display: "inline-flex",
          gap: "3px",
          alignItems: "center",
        }}
      >
        Tarka is thinking
        <span
          style={{
            display: "inline-block",
            width: "20px",
            letterSpacing: "1px",
          }}
        >
          {".".repeat(dots)}
        </span>
      </span>
    </div>
  );
};

export default TypingIndicator;
