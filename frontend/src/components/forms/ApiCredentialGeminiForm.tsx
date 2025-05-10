import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import { Textarea } from "../ui/textarea";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiCredentials } from "@/services/api";
import { AxiosError } from "axios";
import { Loader2 } from "lucide-react";
import { useEffect } from "react";

interface ApiCredentialPayload {
  api_key: string;
}

const provider = "google_gemini";

const formSchema = z.object({
  api_key: z.string().min(1, { message: "API Key is required." }),
});

export function ApiCredentialGeminiForm() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const {
    data: credentialStatusResponse,
    isLoading: isLoadingStatus,
    isError: isErrorStatus,
    error: statusError,
    isSuccess,
  } = useQuery({
    queryKey: ["apiCredentialStatus", provider],
    queryFn: () => apiCredentials.getStatus(provider),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const credentialStatus = credentialStatusResponse?.data;

  const form = useForm<ApiCredentialPayload>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      api_key: "",
    },
  });

  const mutation = useMutation<
    any,
    AxiosError<{ detail?: string }>,
    ApiCredentialPayload
  >({
    mutationFn: async (data: ApiCredentialPayload) => {
      const queryState = queryClient.getQueryState(["apiCredentialStatus", provider]);
      const entryExistsNow = queryState?.status === 'success';

      console.log(`[Mutation Fn Start] Checking condition. Query status from cache: ${queryState?.status}, Derived entryExistsNow: ${entryExistsNow}`);

      if (entryExistsNow) {
        console.log(`[Mutation Fn] Taking UPDATE path based on queryClient state.`);
        const response = await apiCredentials.update(provider, data.api_key);
        return response.data;
      } else {
        console.log(`[Mutation Fn] Taking CREATE path based on queryClient state.`);
        const response = await apiCredentials.create(provider, data.api_key);
        return response.data;
      }
    },
    onSuccess: (data) => {
      toast({
        title: "Success",
        description: data?.message || "Google Gemini API Key saved successfully.",
      });
      queryClient.invalidateQueries({ queryKey: ["apiCredentialStatus", provider] });
      form.reset({ api_key: "" });
    },
    onError: (error) => {
      console.error("Error saving API Key:", error);
      const errorMessage =
        error?.response?.data?.detail ||
        error?.message ||
        "Failed to save API Key.";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    },
  });

  useEffect(() => {
    if (!mutation.isPending && !isLoadingStatus) {
      form.reset({ api_key: "" });
    }
  }, [credentialStatus, isLoadingStatus, mutation.isPending, form]);


  async function onSubmit(values: ApiCredentialPayload) {
    console.log("Submitting values:", values);
    mutation.mutate(values);
  }

  const renderTimeEntryExists = isSuccess;
  let statusText, statusColor, formLabel, buttonLabel;

  buttonLabel = renderTimeEntryExists ? "Update Key" : "Save Key";

  if (renderTimeEntryExists) {
      if (credentialStatus?.api_key_set) {
          statusText = "API Key is set. Enter a new key to update.";
          statusColor = "text-green-600";
          formLabel = "Update Google Gemini API Key";
      } else {
          statusText = "API Key entry exists but key is not set.";
          statusColor = "text-yellow-600";
          formLabel = "Enter Google Gemini API Key";
      }
  } else {
      if (isLoadingStatus) {
          statusText = "Loading status...";
          statusColor = "text-muted-foreground";
      } else if (isErrorStatus) {
          const isNotFound = (statusError as AxiosError)?.response?.status === 404;
          statusText = isNotFound ? "API Key is not set." : "Error loading status.";
          statusColor = isNotFound ? "text-yellow-600" : "text-red-600";
      } else {
          statusText = "API Key status unknown.";
          statusColor = "text-muted-foreground";
      }
      formLabel = "Enter Google Gemini API Key";
  }

  if (isLoadingStatus) {
    return <Loader2 className="mr-2 h-4 w-4 animate-spin" />;
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="api_key"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{formLabel}</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Paste your API Key here"
                  {...field}
                  rows={3}
                  autoComplete="off"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
         <div className="flex justify-between items-center">
             <p className={`text-sm ${statusColor}`}>
                Status: {statusText}
             </p>
            <Button type="submit" disabled={mutation.isPending || isLoadingStatus}>
              {mutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {buttonLabel}
            </Button>
         </div>
      </form>
    </Form>
  );
} 