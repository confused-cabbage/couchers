import ContributorForm from "components/ContributorForm";
import { useAuthContext } from "features/auth/AuthProvider";
import { ContributorForm as ContributorFormPb } from "pb/account_pb";
import { service } from "service";

export default function FeedbackForm() {
  const { authActions, authState } = useAuthContext();

  const handleSubmit = async (form: ContributorFormPb) => {
    authActions.clearError();
    try {
      if (!authState.flowState) {
        authActions.authError(
          "Submitting feedback form without current signup flow in progress"
        );
      }
      authActions.updateSignupState(
        await service.auth.signupFlowFeedback(
          authState.flowState?.flowToken!,
          form
        )
      );
      return true;
    } catch (err) {
      authActions.authError(err.message);
      return false;
    }
  };

  return <ContributorForm processForm={handleSubmit} />;
}
