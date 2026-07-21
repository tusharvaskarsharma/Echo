import { Suspense } from "react";

import { AppNav } from "../../../components/AppNav";
import { EmmyExperience } from "../../../components/EmmyExperience";

export default function EmmyPage() {
  return <><AppNav /><Suspense fallback={<main className="min-h-[calc(100vh-5rem)] bg-background" />}><EmmyExperience /></Suspense></>;
}
