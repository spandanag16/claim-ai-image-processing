import { useState } from "react";
import { useNavigate } from "react-router-dom";

function Review() {
  const navigate = useNavigate();
  const [claim] = useState(() => JSON.parse(localStorage.getItem("claimData")) || {});

  const images = claim?.images || [];

  return (
    <div className="claim-page">
      <header className="claim-header">
        <button className="back-button" onClick={() => navigate("/new-claim/images")}>← Images</button>
        <div className="logo"><span className="logo-icon">AI</span><span>ClaimAI</span></div>
        <div className="claim-id">PIPELINE READY</div>
      </header>
      <main className="claim-container review-container">
        <div className="claim-heading">
          <div className="badge">IMAGE PIPELINE COMPLETE</div>
          <h1>Images are ready for AI processing</h1>
          <p>The original uploads were preserved and a separate 640 × 640 prepared image was created for each file. YOLO damage detection is not enabled yet.</p>
        </div>
        <div className="review-status-card">
          <div><span className="status-dot connected" /><strong>Upload and preprocessing successful</strong></div>
          <span>{images.length} vehicle images prepared</span>
        </div>
        <div className="review-grid">
          {images.map((image) => (
            <article className="review-card" key={image.upload_id}>
              <strong>{image.original_filename}</strong>
              <span>Original: {image.original_image?.width} × {image.original_image?.height}</span>
              <span>Prepared: {image.processed_image?.width} × {image.processed_image?.height}</span>
              <small>YOLO status: {image.yolo?.status || "not_configured"}</small>
            </article>
          ))}
        </div>
        <div className="review-note">
          <strong>Next planned step</strong>
          <p>Train or configure a YOLO model with annotated vehicle-part damage data, then connect its bounding boxes and confidence scores to severity and repair-cost estimation.</p>
        </div>
      </main>
    </div>
  );
}

export default Review;
