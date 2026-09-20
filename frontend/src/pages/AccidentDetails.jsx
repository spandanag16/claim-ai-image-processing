import { Link } from "react-router-dom";

function AccidentDetails() {
  return (
    <div className="app claim-page">
      <header className="claim-header"><Link className="back-button" to="/new-claim">← Vehicle</Link><div className="logo"><span className="logo-icon">AI</span><span>ClaimAI</span></div><div className="claim-id">STEP 02 / 03</div></header>
      <main className="claim-container">
        <div className="claim-heading"><div className="badge">ACCIDENT DETAILS</div><h1>Tell us what happened</h1><p>This demo continues directly to the image-upload stage.</p></div>
        <div className="form-footer"><span>Continue to image upload</span><Link className="primary-btn" to="/new-claim/images">Continue <span>→</span></Link></div>
      </main>
    </div>
  );
}

export default AccidentDetails;

