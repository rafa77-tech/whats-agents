import { redirect } from "next/navigation";

type HomeProps = {
  searchParams?: {
    code?: string;
    next?: string;
  };
};

export default function Home({ searchParams }: HomeProps) {
  if (searchParams?.code) {
    const next = searchParams.next ?? "/";
    const params = new URLSearchParams({ code: searchParams.code, next });
    redirect(`/callback?${params.toString()}`);
  }

  // Redireciona para o dashboard ou login
  redirect("/login");
}
