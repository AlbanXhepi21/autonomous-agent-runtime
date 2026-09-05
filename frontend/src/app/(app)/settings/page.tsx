import { redirect } from "next/navigation";

export default function PersonalSettingsIndexPage() {
  redirect("/settings/profile");
}
