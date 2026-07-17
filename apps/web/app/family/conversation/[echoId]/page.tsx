import { AppNav } from "../../../../components/AppNav";
import { ConversationClient } from "../../../../components/ConversationClient";

export default function ConversationPage({ params }: { params: { echoId: string } }) { return <main><AppNav /><div className="page-wrap"><ConversationClient echoId={params.echoId} /></div></main>; }
