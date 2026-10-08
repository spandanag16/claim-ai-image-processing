import { useNavigate } from "react-router-dom";

const severityLabels = {
  minor: "Minor",
  moderate: "Moderate",
  severe: "Severe",
};

function ClaimReview() {
  const navigate = useNavigate();
  const claim = JSON.parse(localStorage.getItem("claimData") || "{}");
  const analysis = claim.analysis;

  if (!analysis) {
    return (
      <div className="claim-page">
        <main className="claim-container empty-review">
          <div className="badge">NO ANALYSIS FOUND</div>
          <h1>Start with vehicle images</h1>
          <p>Upload at least two images before opening the review.</p>
          <button className="primary-btn" onClick={() => navigate("/new-claim/images")}>Go to image upload <span>→</span></button>
        </main>
      </div>
    );
  }

  return (
    <div className="claim-page">
      <header className="claim-header">
        <button className="back-button" onClick={() => navigate("/new-claim/images")}>← Images</button>
        <div className="logo"><span className="logo-icon">AI</span><span>ClaimAI</span></div>
        <div className="claim-id">ANALYSIS COMPLETE</div>
      </header>

      <main className="claim-container review-container">
        <div className="claim-heading">
          <div className="badge">DAMAGE ASSESSMENT</div>
          <h1>AI analysis results</h1>
          <p>Detected regions are scored across the uploaded images and grouped into a single claim severity.</p>
        </div>

        <section className={`severity-card severity-${analysis.overall_severity}`}>
          <div>
            <span className="result-label">OVERALL SEVERITY</span>
            <strong>{severityLabels[analysis.overall_severity] || analysis.overall_severity}</strong>
          </div>
          <div className="score-value">{Math.round(analysis.overall_score * 100)}<small>/100</small></div>
        </section>

        <section className="result-summary">
          <div><small>IMAGES ANALYZED</small><strong>{analysis.images_analyzed}</strong></div>
          <div><small>AVERAGE SCORE</small><strong>{Math.round(analysis.average_score * 100)}%</strong></div>
          <div><small>DECISION RULE</small><strong>Highest severity</strong></div>
        </section>

        <h2 className="results-title">Detected damage by image</h2>
        <div className="damage-results">
          {analysis.results.map((result) => (
            <article className="damage-result" key={result.filename}>
              <div className="damage-result-top"><strong>{result.filename}</strong><span className={`severity-pill severity-${result.severity}`}>{severityLabels[result.severity]}</span></div>
              <div className="result-meter"><span style={{ width: `${Math.round(result.damage_score * 100)}%` }} /></div>
              <div className="damage-result-bottom"><span>Potential damaged vehicle panel</span><strong>{Math.round(result.damage_score * 100)}% score</strong></div>
            </article>
          ))}
        </div>

        <div className="review-disclaimer">{analysis.disclaimer}</div>
        <div className="form-footer"><span>Prototype assessment complete</span><button className="secondary-btn" onClick={() => navigate("/")}>Finish</button></div>
      </main>
    </div>
  );
}

export default ClaimReview;
