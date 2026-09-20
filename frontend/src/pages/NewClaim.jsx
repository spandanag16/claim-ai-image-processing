import { Link } from "react-router-dom";

function NewClaim() {
  return (
    <div className="app claim-page">
      <header className="claim-header"><div className="logo"><span className="logo-icon">AI</span><span>ClaimAI</span></div><div className="claim-id">NEW CLAIM</div></header>
      <main className="claim-container">
        <div className="claim-heading"><div className="badge">STEP 01 / 03</div><h1>Start your vehicle claim</h1><p>Continue to the accident details, then upload vehicle images for preprocessing.</p></div>
        <div className="form-footer"><span>Ready to continue</span><Link className="primary-btn" to="/new-claim/accident">Continue <span>→</span></Link></div>
      </main>
    </div>
  );
}

export default NewClaim;

