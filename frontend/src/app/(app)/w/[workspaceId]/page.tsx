import { Workbench } from "@/features/workbench/workbench";

export default async function WorkspacePage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return <Workbench workspaceId={workspaceId} />;
}
