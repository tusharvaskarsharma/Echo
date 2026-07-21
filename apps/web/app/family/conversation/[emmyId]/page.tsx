import { AppNav } from "../../../../components/AppNav";
import { ConversationClient } from "../../../../components/ConversationClient";

export default function ConversationPage({ params }: { params: { emmyId: string } }) { return <main><AppNav /><div className="page-wrap"><ConversationClient emmyId={params.emmyId} /></div></main>; }
