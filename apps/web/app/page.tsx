import Link from "next/link";
import { AppNav } from "../components/AppNav";

export default function Home() {
  return <main><AppNav /><section className="landing"><div><p className="eyebrow">A living legacy, built with consent</p><h1>Some stories deserve more than a recording.</h1><p className="lede">Emmy helps families preserve the voice, values, and memories of the people they loveÃ¢â‚¬â€without ever inventing a story.</p><div className="landing-actions"><Link className="button-link" href="/subject/session">Record a story</Link><Link className="text-link" href="/subject/dashboard">Open my legacy Ã¢â€ â€™</Link></div></div><div className="landing-orb"><div className="audio-orb ready"><span /></div><p>Every answer is grounded in a memory you shared.</p></div></section><section className="principles"><div><b>01</b><h2>Only true stories</h2><p>Emmy refuses to guess when a memory is not there.</p></div><div><b>02</b><h2>Consent stays with you</h2><p>Every memory is private, family, or legacyÃ¢â‚¬â€by choice.</p></div><div><b>03</b><h2>Sources stay visible</h2><p>Every response points back to the memory behind it.</p></div></section></main>;
}
