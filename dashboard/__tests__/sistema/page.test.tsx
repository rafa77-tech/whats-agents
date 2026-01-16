import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SistemaPage from "@/app/(dashboard)/sistema/page";

// Mock useToast
vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("SistemaPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(<SistemaPage />);

    expect(screen.getByText("Carregando...")).toBeInTheDocument();
  });

  it("renders pilot mode ACTIVE status correctly", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          pilot_mode: true,
          autonomous_features: {
            discovery_automatico: false,
            oferta_automatica: false,
            reativacao_automatica: false,
            feedback_automatico: false,
          },
        }),
    });

    render(<SistemaPage />);

    await waitFor(() => {
      expect(screen.getByText("ATIVO")).toBeInTheDocument();
      expect(screen.getByText("Modo seguro ativo")).toBeInTheDocument();
    });
  });

  it("renders pilot mode INACTIVE status correctly", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          pilot_mode: false,
          autonomous_features: {
            discovery_automatico: true,
            oferta_automatica: true,
            reativacao_automatica: true,
            feedback_automatico: true,
          },
        }),
    });

    render(<SistemaPage />);

    await waitFor(() => {
      expect(screen.getByText("DESATIVADO")).toBeInTheDocument();
      expect(screen.getByText("Julia autonoma")).toBeInTheDocument();
    });
  });

  it("shows all autonomous feature cards", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          pilot_mode: false,
          autonomous_features: {
            discovery_automatico: true,
            oferta_automatica: true,
            reativacao_automatica: true,
            feedback_automatico: true,
          },
        }),
    });

    render(<SistemaPage />);

    await waitFor(() => {
      expect(screen.getByText("Discovery Automatico")).toBeInTheDocument();
      expect(screen.getByText("Oferta Automatica")).toBeInTheDocument();
      expect(screen.getByText("Reativacao Automatica")).toBeInTheDocument();
      expect(screen.getByText("Feedback Automatico")).toBeInTheDocument();
    });
  });

  it("shows rate limiting card", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          pilot_mode: true,
          autonomous_features: {
            discovery_automatico: false,
            oferta_automatica: false,
            reativacao_automatica: false,
            feedback_automatico: false,
          },
        }),
    });

    render(<SistemaPage />);

    await waitFor(() => {
      expect(screen.getByText("Rate Limiting")).toBeInTheDocument();
      expect(screen.getByText("20")).toBeInTheDocument(); // msgs por hora
      expect(screen.getByText("100")).toBeInTheDocument(); // msgs por dia
    });
  });

  it("shows operating hours card", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          pilot_mode: true,
          autonomous_features: {
            discovery_automatico: false,
            oferta_automatica: false,
            reativacao_automatica: false,
            feedback_automatico: false,
          },
        }),
    });

    render(<SistemaPage />);

    await waitFor(() => {
      expect(screen.getByText("Horario de Operacao")).toBeInTheDocument();
      expect(screen.getByText("08h as 20h")).toBeInTheDocument();
      expect(screen.getByText("Segunda a Sexta")).toBeInTheDocument();
    });
  });

  it("opens enable confirmation dialog when switch is toggled", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          pilot_mode: false,
          autonomous_features: {
            discovery_automatico: true,
            oferta_automatica: true,
            reativacao_automatica: true,
            feedback_automatico: true,
          },
        }),
    });

    render(<SistemaPage />);

    await waitFor(() => {
      expect(screen.getByText("DESATIVADO")).toBeInTheDocument();
    });

    // Find and click the switch
    const switchElement = screen.getByRole("switch");
    fireEvent.click(switchElement);

    await waitFor(() => {
      expect(screen.getByText("Ativar Modo Piloto?")).toBeInTheDocument();
    });
  });

  it("opens disable confirmation dialog when switch is toggled", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          pilot_mode: true,
          autonomous_features: {
            discovery_automatico: false,
            oferta_automatica: false,
            reativacao_automatica: false,
            feedback_automatico: false,
          },
        }),
    });

    render(<SistemaPage />);

    await waitFor(() => {
      expect(screen.getByText("ATIVO")).toBeInTheDocument();
    });

    // Find and click the switch
    const switchElement = screen.getByRole("switch");
    fireEvent.click(switchElement);

    await waitFor(() => {
      expect(screen.getByText("Desativar Modo Piloto?")).toBeInTheDocument();
      expect(screen.getByText(/Atencao: acao significativa/)).toBeInTheDocument();
    });
  });

  it("shows last changed info when available", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          pilot_mode: true,
          autonomous_features: {
            discovery_automatico: false,
            oferta_automatica: false,
            reativacao_automatica: false,
            feedback_automatico: false,
          },
          last_changed_at: "2026-01-16T10:00:00Z",
          last_changed_by: "admin@revoluna.com",
        }),
    });

    render(<SistemaPage />);

    await waitFor(() => {
      expect(screen.getByText(/Ultima alteracao:/)).toBeInTheDocument();
      expect(screen.getByText(/admin@revoluna.com/)).toBeInTheDocument();
    });
  });

  it("handles API error gracefully", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    render(<SistemaPage />);

    // Should still show the page after loading (empty state from error)
    await waitFor(() => {
      expect(screen.queryByText("Carregando...")).not.toBeInTheDocument();
    });
  });
});
