export default function LoadingIndicator() {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "flex-start",
        marginBottom: "12px",
      }}
    >
      <div
        style={{
          padding: "12px 16px",
          borderRadius: "18px 18px 18px 4px",
          backgroundColor: "#f1f5f9",
          color: "#64748b",
          fontSize: "15px",
          fontStyle: "italic",
          boxShadow: "0 1px 2px rgba(0,0,0,0.08)",
        }}
      >
        Tarka is thinking...
      </div>
    </div>
  );
}
