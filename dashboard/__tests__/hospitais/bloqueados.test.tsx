import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import HospitaisBloqueadosPage from "@/app/(dashboard)/hospitais/bloqueados/page";

// Mock useToast
vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

// Mock fetch with URL handling
const mockFetch = vi.fn();

function setupMockFetch(options: {
  bloqueados?: unknown[];
  historico?: unknown[];
  hospitais?: unknown[];
}) {
  mockFetch.mockImplementation((url: string) => {
    if (url === "/api/hospitais/bloqueados?historico=true") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options.historico ?? []),
      });
    }
    if (url === "/api/hospitais/bloqueados") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options.bloqueados ?? []),
      });
    }
    if (url.startsWith("/api/hospitais")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options.hospitais ?? []),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve([]),
    });
  });
}

describe("HospitaisBloqueadosPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows loading state initially", () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(<HospitaisBloqueadosPage />);

    // Should show loading spinner in table
    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("renders page title and description", async () => {
    setupMockFetch({ bloqueados: [] });

    render(<HospitaisBloqueadosPage />);

    expect(screen.getByText("Hospitais Bloqueados")).toBeInTheDocument();
    expect(
      screen.getByText("Julia nao oferece vagas de hospitais bloqueados")
    ).toBeInTheDocument();
  });

  it("shows empty state when no hospitals blocked", async () => {
    setupMockFetch({ bloqueados: [] });

    render(<HospitaisBloqueadosPage />);

    await waitFor(() => {
      expect(screen.getByText("Nenhum hospital bloqueado")).toBeInTheDocument();
    });
  });

  it("renders blocked hospitals list", async () => {
    setupMockFetch({
      bloqueados: [
        {
          id: "1",
          hospital_id: "hosp-1",
          motivo: "Problemas de pagamento",
          bloqueado_por: "admin@revoluna.com",
          bloqueado_em: new Date().toISOString(),
          status: "bloqueado",
          vagas_movidas: 3,
          hospitais: {
            nome: "Hospital Sao Luiz",
            cidade: "Sao Paulo",
          },
        },
      ],
    });

    render(<HospitaisBloqueadosPage />);

    await waitFor(() => {
      expect(screen.getByText("Hospital Sao Luiz")).toBeInTheDocument();
      expect(screen.getByText("Sao Paulo")).toBeInTheDocument();
      expect(screen.getByText("Problemas de pagamento")).toBeInTheDocument();
      expect(screen.getByText("3 vagas")).toBeInTheDocument();
    });
  });

  it("shows tabs for ativos and historico", async () => {
    setupMockFetch({ bloqueados: [] });

    render(<HospitaisBloqueadosPage />);

    await waitFor(() => {
      expect(screen.getByText(/Bloqueados Ativos/)).toBeInTheDocument();
      expect(screen.getByText(/Historico/)).toBeInTheDocument();
    });
  });

  it("switches to historico tab and loads history", async () => {
    const user = userEvent.setup();

    setupMockFetch({
      bloqueados: [],
      historico: [
        {
          id: "1",
          hospital_id: "hosp-1",
          motivo: "Antigo problema",
          bloqueado_por: "admin@revoluna.com",
          bloqueado_em: "2026-01-10T10:00:00Z",
          status: "desbloqueado",
          desbloqueado_em: "2026-01-12T15:00:00Z",
          desbloqueado_por: "admin@revoluna.com",
          hospitais: {
            nome: "Hospital Albert Einstein",
            cidade: "Sao Paulo",
          },
        },
      ],
    });

    render(<HospitaisBloqueadosPage />);

    await waitFor(() => {
      expect(screen.getByText(/Bloqueados Ativos/)).toBeInTheDocument();
    });

    // Click on historico tab using role and userEvent
    const tabs = screen.getAllByRole("tab");
    const historicoTab = tabs.find((tab) => tab.textContent?.includes("Historico"));
    expect(historicoTab).toBeDefined();
    if (historicoTab) {
      await user.click(historicoTab);
    }

    await waitFor(() => {
      expect(screen.getByText("Hospital Albert Einstein")).toBeInTheDocument();
      expect(screen.getByText("Desbloqueado")).toBeInTheDocument();
    });
  });

  it("shows Bloquear Hospital button", async () => {
    setupMockFetch({ bloqueados: [] });

    render(<HospitaisBloqueadosPage />);

    await waitFor(() => {
      expect(screen.getByText("Bloquear Hospital")).toBeInTheDocument();
    });
  });

  it("opens bloquear dialog when button is clicked", async () => {
    setupMockFetch({
      bloqueados: [],
      hospitais: [{ id: "hosp-1", nome: "Hospital Teste", cidade: "SP" }],
    });

    render(<HospitaisBloqueadosPage />);

    await waitFor(() => {
      expect(screen.getByText("Bloquear Hospital")).toBeInTheDocument();
    });

    const button = screen.getByText("Bloquear Hospital");
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText("Motivo do bloqueio *")).toBeInTheDocument();
    });
  });

  it("shows Desbloquear button for each blocked hospital", async () => {
    setupMockFetch({
      bloqueados: [
        {
          id: "1",
          hospital_id: "hosp-1",
          motivo: "Teste motivo",
          bloqueado_por: "admin@revoluna.com",
          bloqueado_em: new Date().toISOString(),
          status: "bloqueado",
          vagas_movidas: 0,
          hospitais: { nome: "Hospital Desbloquear", cidade: "SP" },
        },
      ],
    });

    render(<HospitaisBloqueadosPage />);

    await waitFor(() => {
      expect(screen.getByText("Hospital Desbloquear")).toBeInTheDocument();
      expect(screen.getByText("Desbloquear")).toBeInTheDocument();
    });
  });

  it("opens confirmation dialog when Desbloquear is clicked", async () => {
    setupMockFetch({
      bloqueados: [
        {
          id: "1",
          hospital_id: "hosp-1",
          motivo: "Teste motivo dialog",
          bloqueado_por: "admin@revoluna.com",
          bloqueado_em: new Date().toISOString(),
          status: "bloqueado",
          vagas_movidas: 0,
          hospitais: { nome: "Hospital Dialog Teste", cidade: "SP" },
        },
      ],
    });

    render(<HospitaisBloqueadosPage />);

    await waitFor(() => {
      expect(screen.getByText("Hospital Dialog Teste")).toBeInTheDocument();
    });

    // Find the Desbloquear button in the table row
    const desbloquearBtn = screen.getByRole("button", { name: /Desbloquear/i });
    fireEvent.click(desbloquearBtn);

    // Alert dialog should appear
    await waitFor(() => {
      expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    });
  });

  it("shows informative alert about blocking behavior", async () => {
    setupMockFetch({ bloqueados: [] });

    render(<HospitaisBloqueadosPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/Quando um hospital e bloqueado/)
      ).toBeInTheDocument();
    });
  });
});
