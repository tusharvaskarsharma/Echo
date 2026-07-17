import { AppNav } from "../../../components/AppNav";
import { MemoryExperience } from "../../../components/MemoryExperience";

export default function Memories() { return <main className="min-h-screen bg-background"><AppNav /><div className="page-wrap pb-14 pt-10"><p className="eyebrow">Review, connect, and consent</p><h1 className="page-title">Your memory map</h1><p className="mt-3 max-w-2xl text-lg leading-8 text-text/65">Explore the stories you have saved, see the themes that connect them, and choose who may access each one.</p><MemoryExperience compact /></div></main>; }
