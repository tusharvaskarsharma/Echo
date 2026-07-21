import { Suspense } from "react";

import { AppNav } from "../../../components/AppNav";
import { EmmyExperience } from "../../../components/EmmyExperience";

/** The concrete /subject/emmy route used by the dashboard navigation. */
export default function SubjectEmmyPage() {
  return <><AppNav /><Suspense fallback={<main className="min-h-[calc(100vh-5rem)] bg-background" />}><EmmyExperience /></Suspense></>;
}
