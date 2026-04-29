import { Navigate } from "react-router-dom";
import { isLoggedIn } from "../../lib/auth";

type Props = {
  children: React.ReactNode;
};

export default function ProtectedRoute({ children }: Props) {
  if (!isLoggedIn()) {
    return <Navigate to="/login" replace />;
  }

  return children;
}