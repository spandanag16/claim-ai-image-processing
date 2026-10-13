import { useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";

function Review() {
  const navigate = useNavigate();
  const [claim] = useState(() => JSON.parse(localStorage.getItem("claimData")) || {});
  const [report, setReport] = useState(null);
  const [model, setModel] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");

  const images = claim?.images || [];

  const runAnalysis = async () => {
    setError("");
    setIsAnalyzing(true);
    try {
      const response = await API.post("/api/analysis/run", {
        claim_id: claim.claimId || "CLAIM-LOCAL",
        upload_ids: images.map((image) => image.upload_id),
        vehicle: claim.vehicle || {},
        accident: claim.accident || {},
      });
      setReport(response.data.report);
      setModel(response.data.model);
    } catch (analyzeError) {
      setError(analyzeError.response?.data?.detail || "Analysis failed. Check that the backend is running.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="claim-page">
      <header className="claim-header">
        <button className="back-button" onClick={() => navigate("/new-claim/images")}>← Images</button>
        <div className="logo"><span className="logo-icon">AI</span><span>ClaimAI</span></div>
        <div className="claim-id">{report ? report.report_id : "PIPELINE READY"}</div>
      </header>
      <main className="claim-container review-container">
        <div className="claim-heading">
          <div className="badge">{report ? "CLAIM REPORT" : "IMAGE PIPELINE COMPLETE"}</div>
          <h1>{report ? "AI damage assessment complete" : "Images are ready for AI analysis"}</h1>
          <p>
            {report
              ? "The claim report below covers damage detection, severity, repair cost estimation, and recommendations."
              : `${images.length} vehicle image uploaded, validated, resized, denoised, and normalized for the AI pipeline.`}
          </p>
        </div>

        {!report && (
          <div className="review-status-card">
            <div><span className="status-dot connected" /><strong>Upload and preprocessing successful</strong></div>
            <button type="button" className="primary-btn" onClick={runAnalysis} disabled={isAnalyzing || images.length === 0}>
              {isAnalyzing ? "Analyzing…" : "Run AI Damage Analysis"}<span>→</span>
            </button>
          </div>
        )}
        {error && <div className="form-error upload-error">{error}</div>}

        {!report && (
          <div className="review-grid">
            {images.map((image) => (
              <article className="review-card" key={image.upload_id}>
                <strong>{image.original_filename}</strong>
                <span>Original: {image.original_image?.width} × {image.original_image?.height}</span>
                <span>Prepared: {image.processed_image?.width} × {image.processed_image?.height}</span>
                <small>CV preprocessing: {image.ai_ready_image ? "applied" : "fallback (PIL only)"}</small>
              </article>
            ))}
          </div>
        )}

        {report && (
          <div className="report-wrapper">
            <div className={`severity-banner severity-${report.severity.severity.toLowerCase()}`}>
              <div>
                <span className="severity-label">{report.severity.severity}</span>
                <span className="severity-score">Severity score: {report.severity.score} / 100</span>
              </div>
              <div className="severity-cost">
                <span>Estimated repair cost</span>
                <strong>₹ {report.cost_estimate.estimated_repair_cost.toLocaleString("en-IN")}</strong>
              </div>
            </div>

            <section className="report-section">
              <h2>Detected damage</h2>
              {report.damage_summary.damaged_parts.length ? (
                <div className="detection-list">
                  {images.map((image) => {
                    const result = (report.per_image || []).find((r) => r.upload_id === image.upload_id);
                    return result && result.detections.length ? (
                      <article key={image.upload_id} className="review-card">
                        <strong>{image.original_filename}</strong>
                        {result.detections.map((detection, index) => (
                          <span key={index}>
                            {detection.part} · {detection.damage_type} · conf {detection.confidence}
                          </span>
                        ))}
                      </article>
                    ) : null;
                  })}
                </div>
              ) : (
                <p>No damage-suspect regions were detected in the uploaded images.</p>
              )}
              <p className="report-summary">{report.severity.damage_summary}</p>
            </section>

            <section className="report-section">
              <h2>Cost estimation</h2>
              {report.cost_estimate.lines.length ? (
                <table className="cost-table">
                  <thead><tr><th>Part</th><th>Damage</th><th>Parts (₹)</th><th>Labour (₹)</th><th>Subtotal (₹)</th></tr></thead>
                  <tbody>
                    {report.cost_estimate.lines.map((line, index) => (
                      <tr key={index}>
                        <td>{line.part}</td><td>{line.damage_type}</td>
                        <td>{line.parts_cost.toLocaleString("en-IN")}</td>
                        <td>{line.labour_cost.toLocaleString("en-IN")}</td>
                        <td>{line.subtotal.toLocaleString("en-IN")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <p>No cost lines — no damage detected.</p>}
            </section>

            <section className="report-section">
              <h2>Repair recommendations</h2>
              <ul>{report.repair_recommendations.map((r) => <li key={r}>{r}</li>)}</ul>
            </section>

            <section className="report-section">
              <h2>Claim decision support</h2>
              <p><strong>{report.claim_decision_support}</strong></p>
              <p>Vehicle: {report.vehicle?.manufacturer || "—"} {report.vehicle?.model || ""} · Accident: {report.accident?.type || "—"}</p>
            </section>

            <div className="review-note">
              <strong>Model transparency</strong>
              <p>Engine: {report.model_transparency.engines_used.join(", ")}{model ? ` — ${model.message}` : ""}. {report.model_transparency.note}</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default Review;
