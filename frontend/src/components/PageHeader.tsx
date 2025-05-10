import React from 'react';
import { Typography, Box, styled } from '@mui/material';
import PropTypes from 'prop-types';

const PageHeaderWrapper = styled(Box)(
  ({ theme }) => `
    padding: ${theme.spacing(3)};
    margin-bottom: ${theme.spacing(3)};
    background-color: ${theme.palette.background.paper};
    border-radius: ${theme.shape.borderRadius};
  `
);

interface PageHeaderProps {
  title: string;
  subtitle?: string; // Optional subtitle
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle }) => {
  return (
    <PageHeaderWrapper>
      <Typography variant="h3" component="h3" gutterBottom>
        {title}
      </Typography>
      {subtitle && (
        <Typography variant="subtitle2">
          {subtitle}
        </Typography>
      )}
    </PageHeaderWrapper>
  );
};

PageHeader.propTypes = {
  title: PropTypes.string.isRequired,
  subtitle: PropTypes.string
};

export default PageHeader; 