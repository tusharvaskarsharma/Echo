import { Suspense } from "react";

import { AppNav } from "../../../components/AppNav";
import { EchoExperience } from "../../../components/EchoExperience";

/** The concrete /subject/echo route used by the dashboard navigation. */
export default function SubjectEchoPage() {
  return <><AppNav /><Suspense fallback={<main className="min-h-[calc(100vh-5rem)] bg-background" />}><EchoExperience /></Suspense></>;
}
