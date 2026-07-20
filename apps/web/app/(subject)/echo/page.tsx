import { Suspense } from "react";

import { AppNav } from "../../../components/AppNav";
import { EchoExperience } from "../../../components/EchoExperience";

export default function EchoPage() {
  return <><AppNav /><Suspense fallback={<main className="min-h-[calc(100vh-5rem)] bg-background" />}><EchoExperience /></Suspense></>;
}
