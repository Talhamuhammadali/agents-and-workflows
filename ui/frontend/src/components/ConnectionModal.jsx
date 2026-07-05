import { useState } from "react";

const overlay = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.5)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

const panel = {
  background: "#1e1e1e",
  color: "#eee",
  width: "min(560px, 92vw)",
  maxHeight: "90vh",
  overflowY: "auto",
  borderRadius: 10,
  padding: 24,
  border: "1px solid #333",
};

const field = { display: "block", width: "100%", marginTop: 4, marginBottom: 12, padding: "8px 10px", background: "#111", color: "#eee", border: "1px solid #333", borderRadius: 6, boxSizing: "border-box" };
const label = { fontSize: 13, color: "#bbb" };
const row = { display: "flex", alignItems: "center", gap: 8, margin: "10px 0" };
const btn = { padding: "8px 16px", borderRadius: 6, border: "1px solid #444", cursor: "pointer" };

export default function ConnectionModal({ open, onCancel, onCreate }) {
  const [title, setTitle] = useState("");
  const [useLocalMinikube, setUseLocalMinikube] = useState(true);
  const [targetKubeconfig, setTargetKubeconfig] = useState("");
  const [targetNamespace, setTargetNamespace] = useState("default");
  const [allowBash, setAllowBash] = useState(false);
  const [useAws, setUseAws] = useState(false);
  const [accessKeyId, setAccessKeyId] = useState("");
  const [secretAccessKey, setSecretAccessKey] = useState("");
  const [region, setRegion] = useState("");
  const [sessionToken, setSessionToken] = useState("");

  if (!open) return null;

  function submit() {
    const config = {
      use_local_minikube: useLocalMinikube,
      target_kubeconfig: useLocalMinikube ? null : targetKubeconfig || null,
      target_namespace: targetNamespace || "default",
      allow_bash: allowBash,
      aws: useAws
        ? {
            access_key_id: accessKeyId,
            secret_access_key: secretAccessKey,
            region,
            session_token: sessionToken || null,
          }
        : null,
    };
    onCreate(title || null, config);
  }

  return (
    <div style={overlay} onClick={onCancel}>
      <div style={panel} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ marginTop: 0 }}>New chat — connect infrastructure</h2>

        <label style={label}>Chat title (optional)</label>
        <input style={field} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="New chat" />

        <h3>Target cluster</h3>
        <div style={row}>
          <input
            type="checkbox"
            id="use-minikube"
            checked={useLocalMinikube}
            onChange={(e) => setUseLocalMinikube(e.target.checked)}
          />
          <label htmlFor="use-minikube">Use local minikube</label>
        </div>

        {!useLocalMinikube && (
          <>
            <label style={label}>Target kubeconfig (paste `kubectl config view --minify --flatten`)</label>
            <textarea
              style={{ ...field, minHeight: 120, fontFamily: "monospace", fontSize: 12 }}
              value={targetKubeconfig}
              onChange={(e) => setTargetKubeconfig(e.target.value)}
              placeholder="apiVersion: v1&#10;clusters: ..."
            />
          </>
        )}

        <label style={label}>Target namespace</label>
        <input style={field} value={targetNamespace} onChange={(e) => setTargetNamespace(e.target.value)} />

        <h3>AWS source (optional)</h3>
        <div style={row}>
          <input type="checkbox" id="use-aws" checked={useAws} onChange={(e) => setUseAws(e.target.checked)} />
          <label htmlFor="use-aws">Provide AWS credentials</label>
        </div>
        {useAws && (
          <>
            <label style={label}>Access key id</label>
            <input style={field} value={accessKeyId} onChange={(e) => setAccessKeyId(e.target.value)} />
            <label style={label}>Secret access key</label>
            <input
              style={field}
              type="password"
              value={secretAccessKey}
              onChange={(e) => setSecretAccessKey(e.target.value)}
            />
            <label style={label}>Region</label>
            <input style={field} value={region} onChange={(e) => setRegion(e.target.value)} placeholder="us-east-1" />
            <label style={label}>Session token (optional)</label>
            <input style={field} value={sessionToken} onChange={(e) => setSessionToken(e.target.value)} />
          </>
        )}

        <div style={row}>
          <input type="checkbox" id="allow-bash" checked={allowBash} onChange={(e) => setAllowBash(e.target.checked)} />
          <label htmlFor="allow-bash">Allow bash / kubectl (CRD validation — temporary)</label>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
          <button style={{ ...btn, background: "#2a2a2a", color: "#ccc" }} onClick={onCancel}>
            Cancel
          </button>
          <button style={{ ...btn, background: "#2d6cdf", color: "#fff", border: "none" }} onClick={submit}>
            Create chat
          </button>
        </div>
      </div>
    </div>
  );
}
