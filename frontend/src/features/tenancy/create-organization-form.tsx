"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { TenantStateCard } from "@/features/tenancy/tenant-state-card";
import { ApiError } from "@/lib/api/client";
import { workspacesApi } from "@/lib/api/workspaces";
import { rememberWorkspaceId } from "@/lib/auth/last-workspace";

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function CreateOrganizationForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{ name?: string; slug?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onNameChange = (value: string) => {
    setName(value);
    if (!slugTouched) setSlug(slugify(value));
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    const errors: typeof fieldErrors = {};
    if (!name.trim()) errors.name = "Enter an organization name.";
    if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(slug)) {
      errors.slug = "Use lowercase letters, numbers, and hyphens only.";
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      const workspace = await workspacesApi.create({
        name: name.trim(),
        slug,
        default_timezone: "UTC",
        default_locale: "en-US",
        default_currency: "USD",
      });
      rememberWorkspaceId(workspace.id);
      router.push(`/w/${workspace.id}`);
    } catch (error) {
      if (error instanceof ApiError && error.code === "slug_already_exists") {
        setFieldErrors((current) => ({ ...current, slug: error.message }));
      } else {
        setFormError("This organization could not be created. Try again.");
      }
      setSubmitting(false);
    }
  };

  return (
    <TenantStateCard title="Create an organization">
      {formError ? (
        <p className="form-banner error" role="alert">
          {formError}
        </p>
      ) : null}
      <form className="auth-form" onSubmit={onSubmit} noValidate>
        <div className="field">
          <label htmlFor="org-name">Organization name</label>
          <input
            id="org-name"
            type="text"
            value={name}
            onChange={(event) => onNameChange(event.target.value)}
            aria-invalid={fieldErrors.name ? "true" : undefined}
            required
          />
          {fieldErrors.name ? (
            <p className="field-error" role="alert">
              {fieldErrors.name}
            </p>
          ) : null}
        </div>
        <div className="field">
          <label htmlFor="org-slug">Slug</label>
          <input
            id="org-slug"
            type="text"
            value={slug}
            onChange={(event) => {
              setSlugTouched(true);
              setSlug(event.target.value);
            }}
            aria-invalid={fieldErrors.slug ? "true" : undefined}
            required
          />
          <p className="field-hint">Used in URLs. Lowercase letters, numbers, and hyphens.</p>
          {fieldErrors.slug ? (
            <p className="field-error" role="alert">
              {fieldErrors.slug}
            </p>
          ) : null}
        </div>
        <div className="tenant-state-actions">
          <button
            className="tenant-state-primary"
            type="submit"
            disabled={submitting}
            style={{ border: 0 }}
          >
            {submitting ? "Creating…" : "Create organization"}
          </button>
        </div>
      </form>
    </TenantStateCard>
  );
}
