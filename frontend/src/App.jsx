import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import NewClaim from "./pages/NewClaim";
import AccidentDetails from "./pages/AccidentDetails";
import ImageUpload from "./pages/ImageUpload";
import ClaimReview from "./pages/ClaimReview";

import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* Home */}
        <Route
          path="/"
          element={<Home />}
        />

        {/* Step 1 */}
        <Route
          path="/new-claim"
          element={<NewClaim />}
        />

        {/* Step 2 */}
        <Route
          path="/new-claim/accident"
          element={<AccidentDetails />}
        />

        {/* Step 3 */}
        <Route
          path="/new-claim/images"
          element={<ImageUpload />}
        />

        <Route
          path="/claim/review"
          element={<ClaimReview />}
        />

      </Routes>
    </BrowserRouter>
  );
}

export default App;
